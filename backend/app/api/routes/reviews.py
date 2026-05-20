from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User, UserRole
from app.models.review import Review
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.services.ai_chat import analyze_review_sentiment

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _enrich(review: Review, db: Session) -> dict:
    patient = db.query(Patient).filter(Patient.id == review.patient_id).first()
    patient_name = None
    if patient and patient.user:
        fn = patient.user.first_name or ""
        ln = patient.user.last_name or ""
        patient_name = (fn + " " + ln).strip() or patient.user.email

    return {
        "id": str(review.id),
        "patient_id": str(review.patient_id),
        "doctor_id": str(review.doctor_id),
        "appointment_id": str(review.appointment_id),
        "rating": review.rating,
        "comment": review.comment,
        "sentiment": review.sentiment,   # Feature 14
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "patient_name": patient_name,
    }


def _run_sentiment_analysis(review_id: UUID, comment: str, rating: int, db: Session) -> None:
    """Rulează sentiment analysis în background și salvează rezultatul."""
    try:
        sentiment = analyze_review_sentiment(comment, rating)
        db.query(Review).filter(Review.id == review_id).update({"sentiment": sentiment})
        db.commit()
    except Exception:
        pass


@router.post("/")
def create_review(
    data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Only patients can leave reviews")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    appointment_id = data.get("appointment_id")
    rating = data.get("rating")
    comment = data.get("comment")

    if not appointment_id or not rating:
        raise HTTPException(status_code=400, detail="appointment_id and rating are required")

    if not (1 <= int(rating) <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Verifică că programarea aparține pacientului și e completed
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient.id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != AppointmentStatus.completed:
        raise HTTPException(status_code=400, detail="Can only review completed appointments")

    # Verifică dacă există deja o recenzie pentru această programare
    existing = db.query(Review).filter(Review.appointment_id == appointment_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists for this appointment")

    # Găsește doctor_id (doctors.id) din appointment.doctor_id (users.id)
    doctor = db.query(Doctor).filter(Doctor.user_id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    review = Review(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_id=appointment.id,
        rating=int(rating),
        comment=comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Feature 14 — analizează sentimentul în background (non-blocking)
    background_tasks.add_task(
        _run_sentiment_analysis,
        review.id,
        comment or "",
        int(rating),
        db,
    )

    return _enrich(review, db)


@router.get("/doctor/{doctor_user_id}")
def get_doctor_reviews(
    doctor_user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = db.query(Doctor).filter(Doctor.user_id == doctor_user_id).first()
    if not doctor:
        return []

    reviews = db.query(Review).filter(Review.doctor_id == doctor.id).order_by(
        Review.created_at.desc()
    ).all()
    return [_enrich(r, db) for r in reviews]


@router.get("/my")
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []
    reviews = db.query(Review).filter(Review.patient_id == patient.id).all()
    return [_enrich(r, db) for r in reviews]


@router.get("/check/{appointment_id}")
def check_review(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Review).filter(Review.appointment_id == appointment_id).first()
    return {"reviewed": existing is not None}
