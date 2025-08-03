from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class OrganizationCreate(BaseModel):
    name: str
    
class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_on: datetime
    owner_id: str
    is_active: bool

    class Config:
        from_attributes = True

class OrganizationMember(BaseModel):
    user_id: str
    organization_id: str