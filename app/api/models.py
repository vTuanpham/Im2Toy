from typing import Union
from pydantic import BaseModel


class TransformResponse(BaseModel):
    success: bool
    image_url: Union[str, None] = None
    image_bytes: Union[str, None] = None
    description: Union[str, None] = None
    error: Union[str, None] = None
