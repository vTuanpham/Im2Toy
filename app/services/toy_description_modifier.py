import logging
from typing import Dict, List
import google.generativeai as genai
from PIL import Image
from numpy import log
from .base_service import BaseService
from ..core.prompt_manager import PromptManager, PromptSequenceItem


logger = logging.getLogger("toy_transformer")


class ToyDescriptionModifier(BaseService):
    def __init__(self, config: Dict, prompt_manager: PromptManager):
        super().__init__(
            config,
            prompt_manager,
            prompt_type="toy_desc_modifier",
            max_concurrency=2,
            max_total_tasks=2,
        )
        self.model = genai.GenerativeModel(
            config["model_name"],
            system_instruction=self._get_prompt_key("system_prompt"),
        )

    async def forward(
        self,
        image: Image.Image,
        org_description: str,
    ) -> str:
        sequence = self._get_prompt_sequence(
            "toy_desc_modifier", exclude_keys=["system_prompt"]
        )
        sequence.items.append(PromptSequenceItem("image", image))
        sequence.items.append(
            PromptSequenceItem("text", f"Original description: {org_description}")
        )

        response = self.model.generate_content(sequence.get_sequence())
        return response.text

    def process_results(self, results: List[str]) -> str:
        longest_toy_description = max(results, key=len)
        logger.log(logging.INFO, f"Longest toy description: {longest_toy_description}")
        return longest_toy_description
