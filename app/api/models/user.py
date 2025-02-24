from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from bson import ObjectId

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    hashed_password: str
    google_id: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    class Config:
        json_encoders = {ObjectId: str}

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    google_id: Optional[str] = None
    disabled: Optional[bool] = None

class GoogleUserCreate(BaseModel):
    google_id: str
    email: EmailStr
    full_name: Optional[str] = None
