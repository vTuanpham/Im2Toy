import logging
from typing import Dict, List
from typing_extensions import TypedDict
import google.generativeai as genai
from PIL import Image
from fuzzywuzzy import fuzz
from collections import Counter
from .base_service import BaseService
from ..core.prompt_manager import PromptManager, PromptSequenceItem


logger = logging.getLogger("toy_transformer")


class KeywordResponse(TypedDict):
    reasoning: str  # Keep this as reasoning instead of short_reasoning as for some reason the model will return correct if the key is different from the N-shot prompt
    main_objects: List[str]


class KeywordExtractor(BaseService):
    def __init__(self, config: Dict, prompt_manager: PromptManager):
        super().__init__(
            config,
            prompt_manager,
            prompt_type="keyword_extractor",
            max_concurrency=4,
            max_total_tasks=4,
        )
        self.model = genai.GenerativeModel(
            config["model_name"],
            system_instruction=self._get_prompt_key("system_prompt"),
        )

    async def forward(self, image: Image.Image) -> str:
        sequence = self._get_prompt_sequence(
            "keyword_extractor", exclude_keys=["system_prompt"]
        )
        sequence.items.append(PromptSequenceItem("image", image))

        response = self.model.generate_content(
            sequence.get_sequence(),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=KeywordResponse,
                max_output_tokens=512,
                # temperature=0.65,
                # top_p=0.355,
                # top_k=35,
            ),
        )

        # Inital eval to check if the response is a valid dict
        eval(response.text)

        return response.text

    def process_results(self, results: List[str]) -> KeywordResponse:
        # Join all the results to their corresponding keys if they contain the "main_objects" key
        final_result = KeywordResponse(reasoning="", main_objects=[])

        logger.log(logging.INFO, f"Processing results: {results}")

        for result_str in results:
            try:
                result = eval(result_str)
                if not isinstance(result, dict):
                    raise ValueError("Result is not a dictionary")
                if "main_objects" not in result:
                    raise ValueError("Result does not contain 'main_objects' key")
                if not isinstance(result["main_objects"], list):
                    raise ValueError("'main_objects' key is not a list")
                if "reasoning" not in result:
                    raise ValueError("Result does not contain 'reasoning' key")
                if not isinstance(result["reasoning"], str):
                    raise ValueError("'reasoning' key is not a string")
            except Exception as e:
                logger.log(logging.ERROR, f"Error evaluating result: {e}")
                continue

            for key, value in result.items():
                if key not in final_result:
                    final_result[key] = []
                if key == "main_objects":
                    final_result[key].extend(value)

        logger.log(logging.INFO, f"Final result before fuzzy matching: {final_result}")

        if len(final_result["main_objects"]) == 0:
            logger.log(logging.ERROR, "No main objects detected")
            raise ValueError("No main objects detected")

        if len(results) > 1:
            final_result_filtered = final_result.copy()
            # Loop through the final result and fuzzy match the characters in the main_objects and filter out the ones that are unique or have a low match
            final_result_filtered["main_objects"] = self._get_frequent_matched_items(
                final_result["main_objects"]
            )
            if len(final_result_filtered["main_objects"]) == 0:
                logger.log(logging.INFO, "No main objects detected")
                logger.log(logging.INFO, "Fall back to the original result")
                final_result_filtered["main_objects"] = final_result["main_objects"]
                final_result["main_objects"] = final_result_filtered["main_objects"]

        logger.log(logging.INFO, f"Final result: {final_result}")
        return final_result

    def _get_frequent_matched_items(self, items, threshold=70, min_frequency=3):
        """
        Returns a list of unique items that highly match with others in the original list,
        filtering out items that appear infrequently.

        Args:
        - items (list): List of strings to filter for frequent, similar items.
        - threshold (int): Minimum fuzzy match score to consider two items similar.
        - min_frequency (int): Minimum number of times a group of similar items should appear to be retained.

        Returns:
        - List of unique, frequently-matched items.
        """
        # Step 1: Group similar items
        clusters = []
        used_items = set()

        for item in items:
            # Skip items that are already part of a cluster
            if item in used_items:
                continue

            # Find all items that match this item above the threshold
            similar_items = [
                i
                for i in items
                if i not in used_items and fuzz.ratio(item, i) >= threshold
            ]

            # If similar items are found, create a cluster and mark items as used
            if len(similar_items) >= min_frequency:
                clusters.append(similar_items)
                used_items.update(similar_items)

        # Step 2: Select one representative item per cluster
        unique_items = [max(cluster, key=Counter(items).get) for cluster in clusters]

        return unique_items
