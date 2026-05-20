from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class MedicalRecordCreate(BaseModel):
    patient_id: UUID
    record_type: str
    data_encrypted: Optional[Any] = None
    notes_encrypted: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    analysis_result: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    record_type: str
    data_encrypted: Optional[Any] = None
    notes_encrypted: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    analysis_result: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    has_anomaly: Optional[bool] = None
    anomaly_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
