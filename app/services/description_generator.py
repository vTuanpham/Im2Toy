import logging
from typing import Dict, List
import google.generativeai as genai
from PIL import Image
from .base_service import BaseService
from ..core.prompt_manager import PromptManager, PromptSequenceItem


logger = logging.getLogger("toy_transformer")


class DescriptionGenerator(BaseService):
    def __init__(self, config: Dict, prompt_manager: PromptManager):
        super().__init__(
            config,
            prompt_manager,
            prompt_type="image_descriptor",
            max_concurrency=4,
            max_total_tasks=4,
        )
        self.model = genai.GenerativeModel(
            config["model_name"],
            system_instruction=self._get_prompt_key("system_prompt"),
        )

    async def forward(
        self, image: Image.Image, detected_keywords: List[str], main_keyword: str
    ) -> str:
        sequence = self._get_prompt_sequence(
            "image_descriptor", exclude_keys=["system_prompt"]
        )
        sequence.items.append(PromptSequenceItem("image", image))
        sequence.items.append(
            PromptSequenceItem(
                "text",
                f"Keywords: {detected_keywords[:min(4, len(detected_keywords))]}",
            )
        )
        sequence.items.append(
            PromptSequenceItem("text", f"Main keyword of the image: {main_keyword}")
        )

        response = self.model.generate_content(
            sequence.get_sequence(),
            generation_config=genai.GenerationConfig(temperature=0.95),
        )
        return response.text

    def process_results(self, results: List[str]) -> str:
        longest_description = max(results, key=len)
        logger.log(logging.INFO, f"Longest description: {longest_description}")

        return longest_description
