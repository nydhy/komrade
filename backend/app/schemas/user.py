"""User schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "veteran"
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    hashed_password: str
