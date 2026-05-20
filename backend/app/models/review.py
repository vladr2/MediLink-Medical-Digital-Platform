from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

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
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    sentiment = Column(sa.String(20), nullable=True)   # Feature 14: pozitiv / negativ / neutru
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient")
    doctor = relationship("Doctor")
    appointment = relationship("Appointment")

    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_review_appointment"),
    )
