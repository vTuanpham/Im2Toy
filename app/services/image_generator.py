import urllib.parse
import requests
import base64
from io import BytesIO
from PIL import Image
from typing import Dict, Tuple


class ImageGenerator:
    def __init__(self, config: Dict):
        self.base_url = config["base_url"]

    def generate_image(self, description: str, output_path: str) -> Tuple[str, str]:
        escaped_prompt = urllib.parse.quote(description, safe=":/%")
        url = f"{self.base_url}{escaped_prompt}"

        response = requests.get(url)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)

            output_img = Image.open(output_path)
            img_byte_array = BytesIO()
            output_img.save(img_byte_array, format="PNG")
            img_byte_array.seek(0)
            image_bytes = base64.b64encode(img_byte_array.getvalue()).decode("utf-8")

            return image_bytes, url
        else:
            raise Exception(f"Failed to generate image: {response.text}")
