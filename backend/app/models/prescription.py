from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    doctor_id = Column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    appointment_id = Column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True
    )
    medications = Column(JSONB, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient")
    doctor = relationship("Doctor")
    appointment = relationship("Appointment")
