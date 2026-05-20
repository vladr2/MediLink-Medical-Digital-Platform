from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id: Optional[UUID] = None
    doctor_id: UUID
    datetime: datetime
    notes: Optional[str] = None
    reason: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    datetime: Optional[datetime] = None
    reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    datetime: datetime
    status: AppointmentStatus
    notes: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
