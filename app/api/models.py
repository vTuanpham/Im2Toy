from typing import Union, List
from pydantic import BaseModel


class TransformResponse(BaseModel):
    success: bool
    image_url: Union[str, None] = None
    image_bytes: Union[str, None] = None
    description: Union[str, None] = None
    toy_description: Union[str, None] = None
    main_object: Union[str, None] = None
    detected_objects: Union[List[str], None] = None
    error: Union[str, None] = None
