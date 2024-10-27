import os
from pathlib import Path
from typing import Any, Dict, Union
import yaml


class ConfigHandler:
    def __init__(self, config_path: Union[str, None] = None):
        if config_path is None:
            config_path = os.path.join(
                Path(__file__).parent.parent.parent, "config", "config.yaml"
            )
        self.config = self._load_config(config_path)

    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def get_api_config(self) -> Dict[str, Any]:
        return self.config.get("api", {})

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        return self.config.get("models", {}).get(model_name, {})

    def get_image_generation_config(self) -> Dict[str, Any]:
        return self.config.get("image_generation", {})

    def get_storage_config(self) -> Dict[str, Any]:
        return self.config.get("storage", {})
