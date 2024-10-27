from pathlib import Path
from typing import Dict, List, Union, Any
import yaml
from PIL import Image


class PromptSequenceItem:
    def __init__(self, item_type: str, content: Union[str, Image.Image]):
        self.type = item_type
        self.content = content


class PromptSequence:
    def __init__(self, items: List[PromptSequenceItem]):
        self.items = items

    def get_sequence(self) -> List[Union[str, Image.Image]]:
        return [item.content for item in self.items]


class PromptManager:
    def __init__(
        self, config_path: Union[str, Path], assets_base_path: Union[str, Path]
    ):
        self.config = self._load_config(config_path)
        self.assets_base_path = Path(assets_base_path)
        self.image_cache: Dict[str, Image.Image] = {}

    @staticmethod
    def _load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _load_text(self, file_path: str) -> str:
        with open(self.assets_base_path / file_path, "r") as f:
            return f.read().strip()

    def _load_image(self, image_key: str) -> Image.Image:
        if image_key not in self.image_cache:
            image_path = self.config["prompt_assets"]["images"][image_key]
            self.image_cache[image_key] = Image.open(self.assets_base_path / image_path)
        return self.image_cache[image_key]

    def get_prompt_key(self, prompt_type: str, prompt_key: str) -> Any:
        return self.config["prompts"][prompt_type][prompt_key]

    def get_prompt_sequence(
        self, prompt_type: str, exclude_keys: Union[List[str], None, str] = None
    ) -> PromptSequence:
        prompt_config = self.config["prompts"][prompt_type]
        sequence_items = []

        if exclude_keys is not None:
            prompt_keys = [
                key for key in prompt_config.keys() if key not in exclude_keys
            ]
            prompt_config = {key: prompt_config[key] for key in prompt_keys}

        # sequence_items.append(
        #     PromptSequenceItem("text", self._load_text(prompt_config["system_prompt"]))
        # )

        for item in prompt_config["example_sequence"]:
            if item["type"] == "text":
                content = self._load_text(item["content"])
            else:
                content = self._load_image(item["content"])
            sequence_items.append(PromptSequenceItem(item["type"], content))

        sequence_items.append(
            PromptSequenceItem("text", self._load_text(prompt_config["task_prompt"]))
        )

        return PromptSequence(sequence_items)
