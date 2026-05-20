from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.core.encryption import EncryptedString


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    # Date sensibile — criptate automat prin EncryptedString TypeDecorator
    cnp = Column(EncryptedString, nullable=True)
    allergies = Column(EncryptedString, nullable=True)
    chronic_conditions = Column(EncryptedString, nullable=True)
    emergency_contact = Column(EncryptedString, nullable=True)
    emergency_phone = Column(EncryptedString, nullable=True)
    # Date non-sensibile — plaintext
    gender = Column(String, nullable=True)
    blood_type = Column(String(5), nullable=True)
    gdpr_consent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="patient_profile")
    medical_records = relationship("MedicalRecord", back_populates="patient")
