"""
Serviciu reminder programări — rulat periodic de APScheduler.
Trimite email + notificare in-app cu 24h și 1h înainte de programare.
Respectă preferința email_notifications a utilizatorului.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.user import User
from app.services.email_service import send_email, _base_template

logger = logging.getLogger(__name__)


def _reminder_email_html(patient_name: str, dt_str: str, doctor_name: str, label: str) -> str:
    content = f"""
      <h2 style="margin:0 0 8px;font-size:18px;color:#111c2d;">⏰ Reminder programare — {label}</h2>
      <p style="margin:0 0 24px;color:#64748b;font-size:14px;">
        Bună ziua, <strong>{patient_name}</strong>!<br>
        Ai o programare în aproximativ <strong>{label}</strong>.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#f8fafd;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;width:140px;">Data și ora</td>
          <td style="padding:6px 0;font-size:13px;font-weight:500;">{dt_str}</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;">Doctor</td>
          <td style="padding:6px 0;font-size:13px;font-weight:500;">{doctor_name}</td>
        </tr>
      </table>
      <p style="margin:0;color:#64748b;font-size:13px;">
        Dacă nu mai poți ajunge, te rugăm să anulezi programarea din platformă.
      </p>
    """
    return _base_template(f"Reminder programare — {label}", content)


async def send_appointment_reminders() -> None:
    """
    Job APScheduler — rulează la fiecare 5 minute.
    Caută programări confirmed/pending care sunt la 1h sau 24h distanță
    și trimite reminder dacă nu a fost trimis deja.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Window 24h: programări între [now+23h, now+25h]
        window_24h_start = now + timedelta(hours=23)
        window_24h_end   = now + timedelta(hours=25)

        # Window 1h: programări între [now+45min, now+75min]
        window_1h_start = now + timedelta(minutes=45)
        window_1h_end   = now + timedelta(minutes=75)

        appointments_to_check = (
            db.query(Appointment)
            .filter(
                Appointment.status.in_([AppointmentStatus.confirmed, AppointmentStatus.pending]),
                Appointment.datetime >= window_1h_start,
                Appointment.datetime <= window_24h_end,
            )
            .all()
        )

        for appt in appointments_to_check:
            dt = appt.datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Fetch patient + user
            patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
            if not patient:
                continue
            patient_user = db.query(User).filter(User.id == patient.user_id).first()
            if not patient_user:
                continue

            doctor_user = db.query(User).filter(User.id == appt.doctor_id).first()
            doctor_name = (
                f"Dr. {doctor_user.first_name or ''} {doctor_user.last_name or ''}".strip()
                if doctor_user else "Doctor"
            )
            patient_name = (
                f"{patient_user.first_name or ''} {patient_user.last_name or ''}".strip()
                or patient_user.email
            )
            dt_str = dt.strftime("%d.%m.%Y %H:%M")
            email_enabled = patient_user.email_notifications is not False

            # ── Reminder 24h ──
            if not appt.reminder_24h_sent and window_24h_start <= dt <= window_24h_end:
                _send_reminder(
                    db=db, appt=appt, patient_user=patient_user,
                    patient_name=patient_name, doctor_name=doctor_name,
                    dt_str=dt_str, label="24 ore", email_enabled=email_enabled,
                    flag="24h",
                )

            # ── Reminder 1h ──
            if not appt.reminder_1h_sent and window_1h_start <= dt <= window_1h_end:
                _send_reminder(
                    db=db, appt=appt, patient_user=patient_user,
                    patient_name=patient_name, doctor_name=doctor_name,
                    dt_str=dt_str, label="1 oră", email_enabled=email_enabled,
                    flag="1h",
                )

        db.commit()

    except Exception as exc:
        logger.error("Eroare reminder_service: %s", exc)
        db.rollback()
    finally:
        db.close()


def _send_reminder(
    db: Session,
    appt: Appointment,
    patient_user: User,
    patient_name: str,
    doctor_name: str,
    dt_str: str,
    label: str,
    email_enabled: bool,
    flag: str,  # "24h" or "1h"
) -> None:
    """Trimite email + notificare in-app și marchează flag-ul."""
    from app.api.routes.notifications import create_notification

    # In-app notification
    try:
        create_notification(
            db, patient_user.id,
            f"Reminder programare — {label}",
            f"Ai o programare în {label} cu {doctor_name} ({dt_str}).",
            "appointment",
        )
    except Exception as exc:
        logger.warning("Notificare in-app eșuată: %s", exc)

    # Email
    if email_enabled:
        try:
            send_email(
                patient_user.email,
                f"[MediLink] Reminder programare — {label}",
                _reminder_email_html(patient_name, dt_str, doctor_name, label),
            )
        except Exception as exc:
            logger.warning("Email reminder eșuat: %s", exc)

    # Mark flag
    if flag == "24h":
        appt.reminder_24h_sent = True
    else:
        appt.reminder_1h_sent = True
