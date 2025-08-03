from pydantic import BaseModel, EmailStr, HttpUrl, UUID4
# from arrow import Arrow
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    email: EmailStr
    provider: str = "local"

class UserDetails(BaseModel):
    user_uuid: str
    username: str
    # password: Optional[str] = None
    email: EmailStr
    password: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    provider: Optional[str] = None
    sso_id: Optional[str] = None
    phone_number: Optional[str] = None
    phone_country_code: Optional[str] = None
    role_id: Optional[int] = None
    entity_uuid: Optional[str] = None
    is_active: Optional[bool] = False
    created_on: datetime
    profile_pic: Optional[str] = None
    # organizations: List[str] = []  # Add this field
    
    class Config:
        arbitrary_types_allowed = True

class UserSignUp(BaseModel):
    password: str
    email: EmailStr
    first_name: Optional[str] = None
    role_id: Optional[int]
    entity_uuid: Optional[str] = None
    last_name: Optional[str] = None
    provider: str = 'local'

class UserLogin(BaseModel):
    username: str
    password: str
    login_on: datetime
    provider: str = 'local'


class User(BaseModel):
    username: str
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    role_id: Optional[str]
    enitya_uuid: Optional[str]
    provider: Optional[str]
    created_on: Optional[datetime]


    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
    
class UserUpdate(BaseModel):
    username: str
    provider: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str]
    phone_country_code: Optional[str] = None
    phone_number: Optional[str] = None
    profile_pic: Optional[str] = None