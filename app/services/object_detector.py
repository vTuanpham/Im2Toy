import logging
from typing import Dict, List, Union
from typing_extensions import TypedDict
import numpy as np
import numpy.typing as npt
from PIL import Image
from ultralytics import YOLOWorld


logger = logging.getLogger("toy_transformer")


class ObjectDetectorResult(TypedDict):
    boxes_xywh: List[npt.NDArray]
    boxes_xyxy: List[npt.NDArray]
    classes: List[str]
    main_class: Union[str, None]
    highest_score_box_xywh: npt.NDArray
    highest_score_box_xyxy: npt.NDArray


class ObjectDetector:
    def __init__(self, config: Dict):
        self.model = YOLOWorld(config["model_path"])
        self.weighted_score_threshold = config["weighted_score_threshold"]
        self.weight_confidence = config["weight_confidence"]
        self.weight_area = config["weight_area"]
        self.weight_center_proximity = config["weight_center_proximity"]

    def detect_objects(
        self, image: Image.Image, classes: List[str]
    ) -> ObjectDetectorResult:
        self.model.set_classes(classes)
        logger.log(logging.INFO, f"Setting classes: {classes}")

        results = self.model.predict(image)
        logger.log(logging.INFO, f"Results: {results}")

        return self._process_results(results, input_classes=classes, image=image)

    def _process_results(
        self, results, input_classes: List[str], image: Image.Image
    ) -> ObjectDetectorResult:
        boxes_xywh, boxes_xyxy, classes, confs = [], [], [], []

        for result in results:
            for box in result.boxes:
                boxes_xywh.append(box.xywh[0].cpu().numpy())
                boxes_xyxy.append(box.xyxy[0].cpu().numpy())
                classes.append(int(box.cls.item()))
                confs.append(box.conf.item())

        if not boxes_xywh:
            logger.log(logging.INFO, "No objects detected")
            return {
                "boxes_xywh": [],
                "boxes_xyxy": [],
                "main_class": None,
                "classes": [],
                "highest_score_box_xywh": np.array([]),
                "highest_score_box_xyxy": np.array([]),
            }

        normalized_combined_score = self._calculate_score(boxes_xywh, confs, image)
        logger.log(
            logging.INFO, f"Normalized combined score: {normalized_combined_score}"
        )

        # Get the box with the highest combined score
        best_box_index = np.argmax(normalized_combined_score)
        logger.log(logging.INFO, f"Best box index: {best_box_index}")

        # # Extract the box with the highest combined score
        highest_score_box_xywh = boxes_xywh[best_box_index]
        highest_score_box_xyxy = boxes_xyxy[best_box_index]

        max_classes = input_classes[classes[best_box_index]]
        detected_classes = [input_classes[c] for c in classes]

        logger.log(logging.INFO, f"Detected classes: {detected_classes}")
        logger.log(logging.INFO, f"Main object detected: {max_classes}")

        return {
            "boxes_xywh": boxes_xywh,
            "boxes_xyxy": boxes_xyxy,
            "main_class": max_classes,
            "classes": detected_classes,
            "highest_score_box_xywh": highest_score_box_xywh,
            "highest_score_box_xyxy": highest_score_box_xyxy,
        }

    def _calculate_score(
        self,
        boxes_xywh: List[np.ndarray],
        confs: List[float],
        image: Image.Image,
    ) -> npt.NDArray:
        # Image dimensions
        image_width, image_height = image.size

        # Calculate image center
        image_center_x, image_center_y = image_width / 2, image_height / 2
        del image

        # Initialize lists to store scores for each condition
        combined_scores = []

        for i, box in enumerate(boxes_xywh):
            # Calculate area of the bounding box (width * height)
            area = box[2] * box[3]

            # Calculate confidence score for the box
            confidence = confs[i]

            # Calculate proximity to the image center
            box_center_x, box_center_y = box[0], box[1]
            distance_to_center = np.sqrt(
                (box_center_x - image_center_x) ** 2
                + (box_center_y - image_center_y) ** 2
            )
            normalized_distance = (
                1
                - (distance_to_center / np.sqrt(image_width**2 + image_height**2)) ** 2
            )

            # Calculate combined score using weighted factors
            combined_score = (
                self.weighted_score_threshold * confidence
                + self.weight_area * (area / (image_width * image_height))
                + self.weight_center_proximity * normalized_distance
            )
            combined_scores.append(combined_score)

        normalized_combined_score = np.interp(
            combined_scores, (min(combined_scores), max(combined_scores)), (0, 1)
        )

        return normalized_combined_score
