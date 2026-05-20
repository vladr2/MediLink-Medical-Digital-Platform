from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.core.encryption import EncryptedString


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    record_type = Column(String(50), nullable=False)
    # Câmpuri medicale sensibile — criptate automat prin EncryptedString TypeDecorator
    notes_encrypted = Column(EncryptedString, nullable=True)
    diagnosis = Column(EncryptedString, nullable=True)
    treatment = Column(EncryptedString, nullable=True)
    analysis_result = Column(EncryptedString, nullable=True)
    # Metadate non-sensibile — plaintext
    data_encrypted = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    has_anomaly = Column(Boolean, nullable=True)
    anomaly_notes = Column(String(500), nullable=True)

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("User", foreign_keys=[doctor_id])
