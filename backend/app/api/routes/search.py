from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User, UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/")
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feature 13 — Caută simultan în doctori, pacienți (staff), programări."""
    term = f"%{q.strip().lower()}%"
    results = {"doctors": [], "patients": [], "appointments": []}

    # ── Doctori — toți utilizatorii ──────────────────────────────────────────
    doctors = (
        db.query(Doctor, User)
        .join(User, Doctor.user_id == User.id)
        .filter(
            User.is_active == True,
            (func.lower(func.coalesce(User.first_name, '')).like(term))
            | (func.lower(func.coalesce(User.last_name, '')).like(term))
            | (func.lower(User.email).like(term))
            | (func.lower(func.coalesce(Doctor.specialization, '')).like(term)),
        )
        .limit(5)
        .all()
    )
    for doc, usr in doctors:
        name = f"{usr.first_name or ''} {usr.last_name or ''}".strip() or usr.email
        results["doctors"].append({
            "id": str(doc.id),
            "user_id": str(doc.user_id),
            "name": name,
            "specialization": doc.specialization or "",
        })

    # ── Pacienți — doar staff ────────────────────────────────────────────────
    if current_user.role in [UserRole.doctor, UserRole.admin, UserRole.assistant]:
        patients = (
            db.query(Patient, User)
            .join(User, Patient.user_id == User.id)
            .filter(
                User.is_active == True,
                (func.lower(func.coalesce(User.first_name, '')).like(term))
                | (func.lower(func.coalesce(User.last_name, '')).like(term))
                | (func.lower(User.email).like(term)),
            )
            .limit(5)
            .all()
        )
        for pat, usr in patients:
            name = f"{usr.first_name or ''} {usr.last_name or ''}".strip() or usr.email
            results["patients"].append({
                "id": str(pat.id),
                "user_id": str(usr.id),
                "name": name,
                "email": usr.email,
            })

    # ── Programări ────────────────────────────────────────────────────────────
    appt_q = db.query(Appointment).filter(
        (func.lower(func.coalesce(Appointment.reason, '')).like(term))
        | (func.lower(func.coalesce(Appointment.notes, '')).like(term))
    )
    if current_user.role == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            appt_q = appt_q.filter(Appointment.patient_id == patient.id)
    elif current_user.role == UserRole.doctor:
        appt_q = appt_q.filter(Appointment.doctor_id == current_user.id)

    for a in appt_q.limit(5).all():
        results["appointments"].append({
            "id": str(a.id),
            "datetime": a.datetime.isoformat() if a.datetime else None,
            "status": a.status,
            "reason": a.reason or "",
        })

    return results
