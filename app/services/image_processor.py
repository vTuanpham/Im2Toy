import os
import logging
from typing import Dict, Any, Tuple
from pathlib import Path
import tempfile
from fastapi import UploadFile
from PIL import Image

from ..core.config import ConfigHandler
from ..core.prompt_manager import PromptManager
from .keyword_extractor import KeywordExtractor
from .object_detector import ObjectDetector
from .segmentation import Segmentation
from .description_generator import DescriptionGenerator
from .image_generator import ImageGenerator
from .toy_description_modifier import ToyDescriptionModifier


logger = logging.getLogger("toy_transformer")


class ImageProcessor:
    def __init__(self, config: ConfigHandler):
        self.config = config
        self.prompt_manager = PromptManager(
            config_path=Path("config/prompts_config.yaml"),
            assets_base_path=Path("assets"),
        )

        # Initialize services
        self.keyword_extractor = KeywordExtractor(
            config.get_model_config("gemini"), self.prompt_manager
        )
        self.object_detector = ObjectDetector(config.get_model_config("yolo"))
        self.segmentation = Segmentation(config.get_model_config("sam"))
        self.description_generator = DescriptionGenerator(
            config.get_model_config("gemini"), self.prompt_manager
        )
        self.toy_description_modifier = ToyDescriptionModifier(
            config.get_model_config("gemini"), self.prompt_manager
        )

        self.image_generator = ImageGenerator(config.get_image_generation_config())

        self.max_output_storage = config.get_storage_config().get(
            "max_output_storage", 30
        )
        self.output_dir = Path(config.get_storage_config()["output_dir"])

        logger.log(logging.INFO, "ImageProcessor initialized")

    @staticmethod
    def remove_transparency(
        img: Image.Image, bg_colour: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        # Only process if image has transparency
        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            logger.log(logging.INFO, f"Removing transparency from image {img}")

            # Convert image to RGBA if in LA mode, to access alpha channel
            img = img.convert("RGBA")
            alpha = img.split()[-1]

            # Create a new image with the specified background color and paste original on it
            bg = Image.new("RGBA", img.size, bg_colour + (255,))
            bg.paste(img, mask=alpha)

            # Convert to RGB to discard the alpha channel completely
            result = bg.convert("RGB")
            logger.log(
                logging.DEBUG,
                f"Transparency removed and alpha channel discarded for image {img}",
            )
            return result
        else:
            return img

    async def process_image(self, file: UploadFile) -> Dict[str, Any]:
        logger.log(logging.INFO, f"Processing image {file}")

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.log(logging.DEBUG, f"Temporary directory created: {temp_dir}")

            # Save uploaded file
            temp_path = Path(temp_dir) / "input.jpg"
            with open(temp_path, "wb") as f:
                f.write(await file.read())

            fsize = os.path.getsize(temp_path)
            if fsize == 0:
                logger.log(logging.ERROR, f"Uploaded file {temp_path} is empty")
                raise Exception("Uploaded file is empty")
            logger.log(logging.DEBUG, f"File saved size: {fsize}")

            # Process image through pipeline
            try:
                image = Image.open(temp_path)
                logger.log(logging.INFO, f"Image loaded {image}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error loading image: {e}")
                raise e

            image = self.remove_transparency(image)

            # Extract keywords
            try:
                keywords = await self.keyword_extractor(image)
                logger.log(logging.INFO, f"Keywords extracted: {keywords}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error extracting keywords: {e}")
                raise e

            try:
                # Detect objects
                detection_result = self.object_detector.detect_objects(
                    image, keywords["main_objects"]
                )
                if (
                    detection_result["main_class"] is None
                    and detection_result["boxes_xyxy"] == []
                ):
                    raise Exception("No main object detected")
                else:
                    boxes_xywh = detection_result["boxes_xywh"]
                    boxes_xyxy = detection_result["boxes_xyxy"]
                    main_class = detection_result["main_class"]
                    classes_detected = detection_result["classes"]

                    highest_score_box_xywh = detection_result["highest_score_box_xywh"]
                    highest_score_box_xyxy = detection_result["highest_score_box_xyxy"]

                logger.log(logging.INFO, f"Object detected: {main_class}")
                logger.log(logging.INFO, f"Classes detected: {classes_detected}")
                logger.log(logging.INFO, f"Highest score box: {highest_score_box_xyxy}")
                logger.log(logging.DEBUG, f"Boxes detected: {boxes_xyxy}")
                logger.log(logging.DEBUG, f"Boxes detected: {boxes_xywh}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error detecting objects: {e}")
                raise e

            try:
                # Segment main object
                segmentation_result = self.segmentation.segment_object(
                    image, box_xyxy=highest_score_box_xyxy
                )
                logger.log(logging.INFO, f"Object {image} segmented")
                logger.log(logging.DEBUG, f"Object segmented {segmentation_result}")

                if segmentation_result is None:
                    raise Exception("Error segmenting object")
                else:
                    segmented_image = segmentation_result["isolated_object"]
                    segmented_image_box_crop = segmentation_result[
                        "isolated_box_cutout"
                    ]
                    bianry_mask = segmentation_result["binary_mask"]

                # Save segmented image
                seg_path = Path(temp_dir) / "segmented.png"
                logger.log(logging.DEBUG, f"Saving segmented image: {seg_path}")
                segmented_image.save(seg_path)
                logger.log(logging.DEBUG, f"Segmented image saved: {seg_path}")

                # Save box crop
                box_crop_path = Path(temp_dir) / "box_crop.png"
                logger.log(logging.DEBUG, f"Saving box crop: {box_crop_path}")
                segmented_image_box_crop.save(box_crop_path)
                logger.log(logging.DEBUG, f"Box crop saved: {box_crop_path}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error segmenting object: {e}")
                raise e

            try:
                if main_class is None:
                    classes_detected = keywords["main_objects"]
                    logger.log(
                        logging.INFO,
                        f"Main object not detected, fallback to LLM keywords: {classes_detected}",
                    )

                # Generate description
                description = await self.description_generator(
                    Image.open(seg_path),
                    detected_keywords=classes_detected,
                    main_keyword=main_class,
                )
                logger.log(logging.INFO, f"Description generated: {description}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error generating description: {e}")
                raise e

            try:
                # Modify description for toy
                toy_description = await self.toy_description_modifier(
                    Image.open(temp_path), description
                )
                logger.log(logging.INFO, f"Modified toy description: {toy_description}")
            except Exception as e:
                logger.log(logging.ERROR, f"Error modifying description: {e}")
                raise e

            # Check how many files are in the output directory and delete the oldest one if there are more than 30
            files = list(self.output_dir.iterdir())
            if len(files) > self.max_output_storage:
                oldest_file = min(files, key=lambda p: p.stat().st_ctime)
                logger.log(logging.INFO, f"Deleting oldest file: {oldest_file}")
                oldest_file.unlink()

            output_path = self.output_dir / os.path.basename(file.filename)
            image_bytes, image_url = self.image_generator.generate_image(
                toy_description, str(output_path)
            )
            logger.log(logging.INFO, f"Image generated: {image_url}")

            return {
                "image_url": image_url,
                "description": description,
                "image_bytes": image_bytes,
                "toy_description": toy_description,
                "main_object": main_class,
                "detected_objects": classes_detected,
            }
