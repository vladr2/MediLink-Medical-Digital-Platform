from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional


class DoctorBase(BaseModel):
    specialization: str
    license_number: str
    department: Optional[str] = None
    bio: Optional[str] = None
    phone_cabinet: Optional[str] = None
    schedule: Optional[str] = None


class DoctorCreate(DoctorBase):
    pass


class DoctorResponse(DoctorBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class DoctorWithUser(DoctorResponse):
    email: str
    is_active: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
