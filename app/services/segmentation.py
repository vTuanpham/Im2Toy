import logging
from typing import Dict, Tuple
import numpy as np
import numpy.typing as npt
from typing_extensions import TypedDict
from PIL import Image
from ultralytics import SAM


logger = logging.getLogger("toy_transformer")


class SegmentationResult(TypedDict):
    binary_mask: npt.NDArray
    isolated_object: Image.Image
    isolated_box_cutout: Image.Image


class Segmentation:
    def __init__(self, config: Dict):
        self.sam_model = SAM(config["model_path"])

    def segment_object(
        self, image: Image.Image, box_xyxy: npt.NDArray
    ) -> SegmentationResult:
        logger.log(logging.INFO, f"Segmenting object with box {box_xyxy}.")

        box_array = np.asarray(box_xyxy).reshape(-1, 4)
        logger.log(logging.DEBUG, f"Box array shape: {box_array.shape}")
        image_np = np.array(image)

        results = self.sam_model(image_np, bboxes=box_array, device="cpu")
        logger.log(logging.DEBUG, f"Segmentation results: {results}")
        binary_mask = results[0].masks.data.cpu().numpy().squeeze()

        return self._process_segmentation(image_np, binary_mask, box_xyxy)

    def _process_segmentation(
        self, image: npt.NDArray, binary_mask: npt.NDArray, box_xyxy: npt.NDArray
    ) -> SegmentationResult:
        logger.log(logging.INFO, "Processing segmentation results")

        logger.log(logging.DEBUG, f"Image shape: {image.shape}")
        logger.log(logging.DEBUG, f"Binary mask shape: {binary_mask.shape}")
        logger.log(logging.DEBUG, f"Box XYXY shape: {box_xyxy.shape}")

        binary_mask_rgb = np.repeat(binary_mask[:, :, np.newaxis], 3, axis=2)
        logger.log(logging.DEBUG, f"Binary mask RGB shape: {binary_mask_rgb.shape}")

        white_background = np.ones_like(image) * 255
        isolated_object = np.where(binary_mask_rgb, image, white_background)
        logger.log(logging.DEBUG, f"Isolated object shape: {isolated_object.shape}")

        # Cut out the isolated object using thr provided box
        isolated_object_PIL = Image.fromarray(isolated_object)
        isolated_box_cutout = isolated_object_PIL.copy()
        isolated_box_cutout = isolated_box_cutout.crop(box_xyxy)
        logger.log(
            logging.DEBUG, f"Isolated box cutout size: {isolated_box_cutout.size}"
        )

        logger.log(logging.INFO, "Segmentation processing complete")

        return {
            "binary_mask": binary_mask,
            "isolated_object": isolated_object_PIL,
            "isolated_box_cutout": isolated_box_cutout,
        }
