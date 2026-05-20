from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timezone
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_medical_staff
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
)
from app.api.routes.audit_log import log_action
from app.api.routes.notifications import create_notification, get_unread_count, manager
from app.services.email_service import email_new_appointment, email_appointment_status

router = APIRouter(prefix="/appointments", tags=["appointments"])


def auto_update_past_appointments(appointments: list, db: Session) -> None:
    """
    Auto-actualizează programările trecute:
      - confirmed + trecut  → completed  (programarea a avut loc)
      - pending   + trecut  → cancelled  (nu a fost confirmată la timp)
    """
    now = datetime.now(timezone.utc)
    changed = False
    for appt in appointments:
        appt_dt = appt.datetime
        if appt_dt and appt_dt.tzinfo is None:
            appt_dt = appt_dt.replace(tzinfo=timezone.utc)
        if appt_dt and appt_dt < now:
            if appt.status == AppointmentStatus.confirmed:
                appt.status = AppointmentStatus.completed
                changed = True
            elif appt.status == AppointmentStatus.pending:
                appt.status = AppointmentStatus.cancelled
                changed = True
    if changed:
        db.commit()


# Păstrăm alias pentru compatibilitate cu orice alte locuri care ar putea folosi vechiul nume
auto_complete_past_appointments = auto_update_past_appointments


@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        appointments = db.query(Appointment).filter(Appointment.patient_id == patient.id).all()
    elif current_user.role == UserRole.doctor:
        appointments = db.query(Appointment).filter(Appointment.doctor_id == current_user.id).all()
    else:
        appointments = db.query(Appointment).all()

    auto_update_past_appointments(appointments, db)
    return appointments


@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    data: AppointmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        patient_id = patient.id
    else:
        if not data.patient_id:
            raise HTTPException(status_code=400, detail="patient_id required")
        patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        patient_id = data.patient_id

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=data.doctor_id,
        datetime=data.datetime,
        notes=data.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    log_action(db, current_user, "CREATE_APPOINTMENT", "appointments",
               f"Programare creată pentru {appointment.datetime}")

    # Notifică doctorul despre noua programare
    patient_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
    dt_str = appointment.datetime.strftime("%d.%m.%Y %H:%M") if appointment.datetime else ""
    notif = create_notification(
        db, data.doctor_id,
        "Programare nouă",
        f"{patient_name} a solicitat o programare pe {dt_str}",
        "appointment",
    )
    unread = get_unread_count(db, data.doctor_id)
    background_tasks.add_task(
        manager.send_to_user,
        str(data.doctor_id),
        {"type": "new_notification", "unread_count": unread,
         "title": notif.title, "message": notif.message},
    )

    # Email către doctor (dacă are notificările email activate)
    doctor_user = db.query(User).filter(User.id == data.doctor_id).first()
    if doctor_user and doctor_user.email_notifications is not False:
        dt_str = appointment.datetime.strftime("%d.%m.%Y %H:%M") if appointment.datetime else ""
        background_tasks.add_task(
            email_new_appointment,
            doctor_user.email,
            f"{doctor_user.first_name or ''} {doctor_user.last_name or ''}".strip() or doctor_user.email,
            patient_name,
            dt_str,
            data.reason or "",
        )

    return appointment


@router.get("/popular-slots")
def get_popular_slots(
    doctor_id: UUID = Query(..., description="ID-ul doctorului"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 8 — Predicție slot-uri populare.
    Analizează istoricul programărilor confirmate/finalizate ale unui doctor
    și returnează top 5 combinații zi-oră cu cele mai multe programări.
    Util pentru a sugera pacienților ore cu disponibilitate dovedită.
    """
    rows = (
        db.query(
            extract("dow", Appointment.datetime).label("dow"),
            extract("hour", Appointment.datetime).label("hour"),
            func.count().label("cnt"),
        )
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(
                [AppointmentStatus.confirmed, AppointmentStatus.completed]
            ),
        )
        .group_by(
            extract("dow", Appointment.datetime),
            extract("hour", Appointment.datetime),
        )
        .order_by(func.count().desc())
        .limit(5)
        .all()
    )

    # PostgreSQL DOW: 0=Dum, 1=Lun, 2=Mar, 3=Mie, 4=Joi, 5=Vin, 6=Sâm
    day_names = {0: "Dum", 1: "Lun", 2: "Mar", 3: "Mie", 4: "Joi", 5: "Vin", 6: "Sâm"}

    return [
        {
            "day_of_week": int(r.dow),
            "hour": int(r.hour),
            "count": int(r.cnt),
            "label": f"{day_names.get(int(r.dow), 'Zi')} {int(r.hour):02d}:00",
        }
        for r in rows
    ]


@router.get("/weekly-slots")
def get_weekly_slots(
    doctor_id: UUID = Query(...),
    week_start: str = Query(..., description="YYYY-MM-DD — luni săptămânii"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 5 — Heatmap disponibilitate.
    Returnează slot-urile de 30 min (08:00-17:30) pentru 5 zile (Lun-Vin)
    marcând care sunt deja ocupate de programări confirmed/pending.
    """
    from datetime import date, timedelta

    week_date = date.fromisoformat(week_start)
    # Normalizează la luni
    week_date = week_date - timedelta(days=week_date.weekday())

    # Fetch all appointments for that doctor in that week
    week_end = week_date + timedelta(days=5)
    appts = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_([AppointmentStatus.pending, AppointmentStatus.confirmed]),
            Appointment.datetime >= datetime(week_date.year, week_date.month, week_date.day),
            Appointment.datetime < datetime(week_end.year, week_end.month, week_end.day),
        )
        .all()
    )

    # Build set of booked slots: "YYYY-MM-DD HH:MM"
    booked = set()
    for a in appts:
        dt = a.datetime
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        rounded_min = 0 if dt.minute < 30 else 30
        booked.add(f"{dt.date().isoformat()} {dt.hour:02d}:{rounded_min:02d}")

    # Generate 5 days × slots
    days = []
    hours = [f"{h:02d}:{m:02d}" for h in range(8, 18) for m in (0, 30)]
    for i in range(5):
        day = week_date + timedelta(days=i)
        day_slots = []
        for slot_time in hours:
            key = f"{day.isoformat()} {slot_time}"
            day_slots.append({"time": slot_time, "booked": key in booked})
        days.append({
            "date": day.isoformat(),
            "day_label": ["Lun", "Mar", "Mie", "Joi", "Vin"][i],
            "slots": day_slots,
        })

    return {"week_start": week_date.isoformat(), "days": days}


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.cancelled_by_patient:
        raise HTTPException(
            status_code=403, detail="Appointment was cancelled by patient"
        )

    # Blocheaza marcarea ca 'completed' daca programarea nu a avut loc inca
    if data.status == AppointmentStatus.completed:
        now = datetime.now(timezone.utc)
        appt_dt = appointment.datetime
        if appt_dt and appt_dt.tzinfo is None:
            appt_dt = appt_dt.replace(tzinfo=timezone.utc)
        if appt_dt and appt_dt > now:
            raise HTTPException(
                status_code=400,
                detail="Nu poți marca ca finalizată o programare care nu a avut loc încă"
            )

    if current_user.role == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if data.status and data.status != AppointmentStatus.cancelled:
            raise HTTPException(
                status_code=403, detail="Patients can only cancel appointments"
            )
        appointment.cancelled_by_patient = True

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)

    old_status = data.status  # statusul nou aplicat
    db.commit()
    db.refresh(appointment)
    log_action(db, current_user, "UPDATE_APPOINTMENT", "appointments",
               f"Programare {appointment_id} actualizată — status: {appointment.status}")

    # Notifică pacientul când statusul se schimbă
    if data.status and data.status != AppointmentStatus.pending:
        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
        if patient:
            dt_str = appointment.datetime.strftime("%d.%m.%Y %H:%M") if appointment.datetime else ""
            status_messages = {
                AppointmentStatus.confirmed:  ("Programare confirmată",  f"Programarea ta din {dt_str} a fost confirmată."),
                AppointmentStatus.cancelled:  ("Programare anulată",     f"Programarea ta din {dt_str} a fost anulată."),
                AppointmentStatus.completed:  ("Consultație finalizată", f"Consultația din {dt_str} a fost finalizată. Verifică fișa medicală."),
            }
            if appointment.status in status_messages:
                title, message = status_messages[appointment.status]
                notif = create_notification(db, patient.user_id, title, message, "appointment")
                unread = get_unread_count(db, patient.user_id)
                background_tasks.add_task(
                    manager.send_to_user,
                    str(patient.user_id),
                    {"type": "new_notification", "unread_count": unread,
                     "title": notif.title, "message": notif.message},
                )

                # Email către pacient (dacă are notificările email activate)
                patient_user = db.query(User).filter(User.id == patient.user_id).first()
                if patient_user and patient_user.email_notifications is not False:
                    dt_str2 = appointment.datetime.strftime("%d.%m.%Y %H:%M") if appointment.datetime else ""
                    p_name = f"{patient_user.first_name or ''} {patient_user.last_name or ''}".strip() or patient_user.email
                    background_tasks.add_task(
                        email_appointment_status,
                        patient_user.email,
                        p_name,
                        appointment.status.value,
                        dt_str2,
                    )

    return appointment
