from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

VITAL_UNITS = {
    "blood_pressure_sys": "mmHg",
    "blood_pressure_dia": "mmHg",
    "pulse": "bpm",
    "weight": "kg",
    "temperature": "°C",
    "oxygen_sat": "%",
}


class VitalSignCreate(BaseModel):
    vital_type: str
    value: float
    recorded_at: Optional[datetime] = None
    notes: Optional[str] = None


class VitalSignResponse(BaseModel):
    id: UUID
    patient_id: UUID
    vital_type: str
    value: float
    unit: str
    recorded_at: Optional[datetime]
    notes: Optional[str]
    model_config = {"from_attributes": True}
