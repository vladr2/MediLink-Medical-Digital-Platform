from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
import re

BLOOD_TYPES = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


class PatientBase(BaseModel):
    """Schema de bază — fără validatori, folosit pentru răspunsuri (citire din DB)."""
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    cnp: Optional[str] = None
    gender: Optional[str] = None


class PatientCreate(PatientBase):
    """Schema pentru scriere — include validatori stricți pe date de intrare."""

    @field_validator("cnp")
    @classmethod
    def validate_cnp(cls, v):
        if v is not None and v != "":
            if not re.fullmatch(r"\d{13}", v):
                raise ValueError("CNP-ul trebuie sa contina exact 13 cifre")
        return v

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v):
        if v is not None and v != "" and v not in BLOOD_TYPES:
            raise ValueError(f"Grupa sangvina invalida. Valori acceptate: {', '.join(sorted(BLOOD_TYPES))}")
        return v or None  # converteste "" la None

    @field_validator("emergency_phone")
    @classmethod
    def validate_phone(cls, v):
        if v is not None and v != "":
            if not re.fullmatch(r"[\d\s\+\-\(\)]{7,20}", v):
                raise ValueError("Numar de telefon invalid")
        return v or None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v != "" and v not in {"M", "F", "Masculin", "Feminin", "male", "female"}:
            raise ValueError("Gen invalid. Valori acceptate: M, F")
        return v or None  # converteste "" la None


class PatientResponse(PatientBase):
    id: UUID
    user_id: UUID
    gdpr_consent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientWithUser(PatientResponse):
    email: str
    is_active: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
