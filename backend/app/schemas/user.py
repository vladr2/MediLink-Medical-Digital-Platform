from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.user import UserRole
import re


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Parola trebuie să aibă minim 8 caractere")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Parola trebuie să conțină cel puțin o literă mare")
        if not re.search(r"\d", v):
            raise ValueError("Parola trebuie să conțină cel puțin o cifră")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    address: Optional[str] = None
    email_notifications: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
