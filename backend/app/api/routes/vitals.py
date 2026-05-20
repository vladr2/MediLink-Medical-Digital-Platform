import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.models.vital_sign import VitalSign
from app.schemas.vital_sign import VitalSignCreate, VitalSignResponse, VITAL_UNITS
from app.api.routes.notifications import create_notification, manager, get_unread_count
from datetime import datetime, timezone

router = APIRouter(prefix="/vitals", tags=["vitals"])

VITAL_ALERTS = {
    "temperature": [
        (">", 39.5, "🌡️ Temperatură critică", "Temperatura ta de {value}°C depășește 39.5°C. Consultați urgent un medic."),
        ("<", 35.0, "🌡️ Hipotermie", "Temperatura ta de {value}°C este sub 35°C. Consultați urgent un medic."),
    ],
    "pulse": [
        ("<", 40,  "❤️ Bradicardie severă", "Pulsul tău de {value} bpm este periculos de scăzut (< 40 bpm)."),
        (">", 150, "❤️ Tahicardie severă", "Pulsul tău de {value} bpm depășește 150 bpm."),
    ],
    "oxygen_sat": [
        ("<", 90, "🫁 Saturație critică O₂", "Saturația oxigenului de {value}% este sub 90%. Solicitați asistență medicală urgent."),
    ],
    "blood_pressure_sys": [
        (">", 180, "🩺 Hipertensiune critică", "Tensiunea sistolică de {value} mmHg depășește 180 mmHg."),
        ("<", 80,  "🩺 Hipotensiune severă",   "Tensiunea sistolică de {value} mmHg este sub 80 mmHg."),
    ],
    "blood_pressure_dia": [
        (">", 120, "🩺 Tensiune diastolică critică", "Tensiunea diastolică de {value} mmHg depășește 120 mmHg."),
    ],
}


@router.get("/my", response_model=List[VitalSignResponse])
def get_my_vitals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    vitals = db.query(VitalSign).filter(VitalSign.patient_id == patient.id).order_by(VitalSign.recorded_at.asc()).all()
    result = []
    for v in vitals:
        r = VitalSignResponse(
            id=v.id, patient_id=v.patient_id, vital_type=v.vital_type,
            value=v.value, unit=VITAL_UNITS.get(v.vital_type, ""),
            recorded_at=v.recorded_at, notes=v.notes
        )
        result.append(r)
    return result


@router.get("/patient/{patient_id}", response_model=List[VitalSignResponse])
def get_patient_vitals(patient_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # allow doctor/admin/assistant
    if current_user.role not in ["doctor", "admin", "assistant"]:
        raise HTTPException(403, "Access denied")
    vitals = db.query(VitalSign).filter(VitalSign.patient_id == patient_id).order_by(VitalSign.recorded_at.asc()).all()
    result = []
    for v in vitals:
        r = VitalSignResponse(
            id=v.id, patient_id=v.patient_id, vital_type=v.vital_type,
            value=v.value, unit=VITAL_UNITS.get(v.vital_type, ""),
            recorded_at=v.recorded_at, notes=v.notes
        )
        result.append(r)
    return result


@router.post("/", response_model=VitalSignResponse)
async def add_vital(data: VitalSignCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    if data.vital_type not in VITAL_UNITS:
        raise HTTPException(400, f"Invalid vital_type. Valid: {list(VITAL_UNITS.keys())}")
    vital = VitalSign(
        patient_id=patient.id,
        vital_type=data.vital_type,
        value=data.value,
        unit=VITAL_UNITS[data.vital_type],
        recorded_at=data.recorded_at or datetime.now(timezone.utc),
        notes=data.notes,
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)

    for op, threshold, title_tpl, msg_tpl in VITAL_ALERTS.get(vital.vital_type, []):
        triggered = (op == ">" and vital.value > threshold) or (op == "<" and vital.value < threshold)
        if triggered:
            title = title_tpl
            message = msg_tpl.replace("{value}", f"{vital.value:.1f}")
            create_notification(db, current_user.id, title, message, "warning")
            unread = get_unread_count(db, current_user.id)
            await manager.send_to_user(str(current_user.id), {
                "type": "notification",
                "title": title,
                "body": message,
                "unread_count": unread,
            })
            break  # o singură alertă per vital

    return VitalSignResponse(
        id=vital.id, patient_id=vital.patient_id, vital_type=vital.vital_type,
        value=vital.value, unit=VITAL_UNITS.get(vital.vital_type, ""),
        recorded_at=vital.recorded_at, notes=vital.notes
    )


@router.post("/patient/{patient_id}", response_model=VitalSignResponse)
async def add_vital_for_patient(
    patient_id: UUID,
    data: VitalSignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Asistentul adaugă semn vital pentru un pacient (ex. la consultație)."""
    if current_user.role != "assistant":
        raise HTTPException(403, "Doar asistentul poate adăuga vitale pentru pacienți")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    if data.vital_type not in VITAL_UNITS:
        raise HTTPException(400, f"Invalid vital_type. Valid: {list(VITAL_UNITS.keys())}")
    vital = VitalSign(
        patient_id=patient.id,
        vital_type=data.vital_type,
        value=data.value,
        unit=VITAL_UNITS[data.vital_type],
        recorded_at=data.recorded_at or datetime.now(timezone.utc),
        notes=data.notes,
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return VitalSignResponse(
        id=vital.id, patient_id=vital.patient_id, vital_type=vital.vital_type,
        value=vital.value, unit=VITAL_UNITS.get(vital.vital_type, ""),
        recorded_at=vital.recorded_at, notes=vital.notes
    )


@router.delete("/{vital_id}", status_code=204)
def delete_vital(vital_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    vital = db.query(VitalSign).filter(VitalSign.id == vital_id, VitalSign.patient_id == patient.id).first()
    if not vital:
        raise HTTPException(404, "Not found")
    db.delete(vital)
    db.commit()
