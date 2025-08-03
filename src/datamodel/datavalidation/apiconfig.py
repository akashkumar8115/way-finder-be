from pydantic import BaseModel
from typing import Any

# API level data model
class ApiConfig(BaseModel):
    path: str = ''
    status_code: Any = None
    tags: list = ['default']
    summary: str = ''
    response_model: Any = None
    description: str = ''
    response_description: Any = None
    deprecated: bool = False