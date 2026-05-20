from sqlalchemy.orm import Session
from uuid import UUID
from app.models.patient import Patient
from app.models.medical_record import MedicalRecord
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User
from app.models.doctor import Doctor
from app.models.prescription import Prescription


def build_patient_context(patient_id: UUID, db: Session) -> dict:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {}

    user = db.query(User).filter(User.id == patient.user_id).first()

    recent_records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc())
        .limit(5)
        .all()
    )

    upcoming_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.pending,
        )
        .order_by(Appointment.datetime)
        .limit(3)
        .all()
    )

    # ── Prescripții recente ────────────────────────────────────────────────────
    recent_prescriptions = (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .limit(3)
        .all()
    )

    full_name = ""
    if user:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

    return {
        "patient": {
            "name": full_name,
            "email": user.email if user else None,
            "blood_type": patient.blood_type,
            "allergies": patient.allergies,
            "chronic_conditions": patient.chronic_conditions,
        },
        "recent_records": [
            {
                "type": r.record_type,
                "date": r.created_at.strftime("%d.%m.%Y") if r.created_at else "?",
                "diagnosis": r.diagnosis,
                "treatment": r.treatment,
                "analysis_result": r.analysis_result,
                "notes": r.notes_encrypted,
            }
            for r in recent_records
        ],
        "upcoming_appointments": [
            {
                "datetime": a.datetime.strftime("%d.%m.%Y %H:%M") if a.datetime else "?",
                "status": str(a.status),
                "notes": a.notes,
            }
            for a in upcoming_appointments
        ],
        "recent_prescriptions": [
            {
                "date": p.created_at.strftime("%d.%m.%Y") if p.created_at else "?",
                "medications": [
                    f"{m.get('name','')} {m.get('dose','')} — {m.get('frequency','')}"
                    for m in (p.medications or [])
                ],
                "notes": p.notes,
            }
            for p in recent_prescriptions
        ],
    }


def build_system_prompt(context: dict) -> str:
    patient = context.get("patient", {})
    records = context.get("recent_records", [])
    appointments = context.get("upcoming_appointments", [])
    prescriptions = context.get("recent_prescriptions", [])

    patient_name = patient.get("name") or "pacientul"

    prompt = f"""Ești un asistent medical AI pentru platforma MediLink, dedicat pacientului {patient_name}.
Rolul tău este să ajuți pacientul să înțeleagă informații medicale, să navigheze platforma \
și să fie direcționat către doctorul potrivit.

REGULI IMPORTANTE:
- Nu pune diagnostice noi. Întotdeauna recomandă consultarea unui medic.
- Explică termenii medicali în limbaj accesibil când ești întrebat.
- Dacă pacientul descrie simptome urgente (durere toracică severă, dificultăți de respirație, \
pierderea cunoștinței), recomandă imediat serviciile de urgență (112).
- Fii empatic, concis și profesionist.
- Răspunde în limba română. Dacă pacientul scrie în altă limbă, răspunde în acea limbă.
- Folosește formatare clară: **bold** pentru termeni importanți, liste cu - pentru enumerări.

PROFILUL MEDICAL AL PACIENTULUI:
- Grupă sanguină: {patient.get("blood_type") or "necunoscută"}
- Alergii: {patient.get("allergies") or "niciuna înregistrată"}
- Condiții cronice: {patient.get("chronic_conditions") or "niciuna înregistrată"}
"""

    if records:
        prompt += "\nULTIMELE ÎNREGISTRĂRI MEDICALE:\n"
        for r in records:
            prompt += f"- [{r['date']}] {r['type'].upper()}"
            if r.get("diagnosis"):
                prompt += f" | Diagnostic: {r['diagnosis']}"
            if r.get("treatment"):
                prompt += f" | Tratament: {r['treatment']}"
            if r.get("analysis_result"):
                prompt += f" | Analiză: {r['analysis_result']}"
            if r.get("notes"):
                prompt += f" | Note: {r['notes']}"
            prompt += "\n"

    if prescriptions:
        prompt += "\nPRESCRIPȚII RECENTE:\n"
        for p in prescriptions:
            meds = ", ".join(p.get("medications", []))
            prompt += f"- [{p['date']}] {meds}"
            if p.get("notes"):
                prompt += f" ({p['notes']})"
            prompt += "\n"

    if appointments:
        prompt += "\nPROGRAMĂRI VIITOARE:\n"
        for a in appointments:
            prompt += f"- {a['datetime']}: {a['status']}"
            if a.get("notes"):
                prompt += f" — {a['notes']}"
            prompt += "\n"

    return prompt


def get_available_doctors(specialization: str, db: Session) -> list:
    """
    Returnează doctori cu specializarea dată.
    Acum include user_id (pentru navigare frontend) și numele real (first_name + last_name).
    """
    doctors = (
        db.query(Doctor)
        .join(Doctor.user)
        .filter(Doctor.specialization.ilike(f"%{specialization}%"))
        .filter(Doctor.user.has(is_active=True))
        .all()
    )
    return [
        {
            "user_id": str(d.user_id),
            "name": f"{d.user.first_name or ''} {d.user.last_name or ''}".strip() or d.user.email,
            "specialization": d.specialization,
            "department": d.department,
        }
        for d in doctors
    ]
