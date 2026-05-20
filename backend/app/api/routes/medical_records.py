from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.services.ai_chat import detect_analysis_anomalies
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db, SessionLocal
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_medical_staff, require_doctor_or_admin
from app.models.user import User, UserRole
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordResponse
from app.api.routes.audit_log import log_action
from app.api.routes.notifications import create_notification, manager, get_unread_count


async def _notify_patient_new_record(
    patient_user_id: str,
    doctor_name: str,
    record_type: str,
):
    """Trimite notificare in-app + push WS pacientului când doctorul adaugă o înregistrare."""
    db = SessionLocal()
    try:
        type_labels = {
            "consultatie": "consultație",
            "analiza": "analiză",
            "tratament": "tratament",
            "reteta": "rețetă",
            "investigatie": "investigație",
        }
        label = type_labels.get(record_type, record_type)
        title = "📋 Înregistrare medicală nouă"
        message = f"Dr. {doctor_name} a adăugat o {label} în fișa ta medicală."
        notif = create_notification(db, patient_user_id, title, message, "info")
        unread = get_unread_count(db, patient_user_id)
        await manager.send_to_user(str(patient_user_id), {
            "type": "notification",
            "title": title,
            "body": message,
            "unread_count": unread,
        })
    finally:
        db.close()

router = APIRouter(prefix="/medical-records", tags=["medical records"])


@router.get("/patient/{patient_id}", response_model=List[MedicalRecordResponse])
def get_patient_records(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == UserRole.patient:
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )
    log_action(db, current_user, "VIEW_MEDICAL_RECORDS", "medical_records",
               f"Vizualizare fișă medicală pacient {patient_id}")
    return records


@router.post("/", response_model=MedicalRecordResponse)
def create_record(
    data: MedicalRecordCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    record = MedicalRecord(
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        record_type=data.record_type,
        data_encrypted=data.data_encrypted,
        notes_encrypted=data.notes_encrypted,
        diagnosis=data.diagnosis,
        treatment=data.treatment,
        analysis_result=data.analysis_result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, current_user, "CREATE_MEDICAL_RECORD", "medical_records",
               f"Creat înregistrare {data.record_type} pentru pacient {data.patient_id}")

    # Notifică pacientul
    doctor_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
    background_tasks.add_task(
        _notify_patient_new_record,
        str(patient.user_id),
        doctor_name,
        data.record_type,
    )

    if record.record_type == "analiza" and record.analysis_result:
        background_tasks.add_task(
            detect_analysis_anomalies, record.id, record.analysis_result, db
        )
    return record


@router.delete("/{record_id}")
def delete_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    log_action(db, current_user, "DELETE_MEDICAL_RECORD", "medical_records",
               f"Șters înregistrare {record_id} (tip: {record.record_type})")
    db.delete(record)
    db.commit()
    return {"message": "Record deleted"}
