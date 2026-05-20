import json as json_lib
import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from groq import Groq
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.models.vital_sign import VitalSign
from app.schemas.vital_sign import VITAL_UNITS

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/patient/{patient_id}")
def get_patient_risk(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # ── Fetch patient — 404 must propagate ───────────────────────────────────
    patient = db.query(Patient).filter(Patient.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # ── All remaining logic wrapped so any error triggers the fallback ────────
    chronic = ""
    medical_records: list = []

    try:
        patient_user = db.query(User).filter(User.id == patient_id).first()

        vitals = (
            db.query(VitalSign)
            .filter(VitalSign.patient_id == patient.id)
            .order_by(VitalSign.recorded_at.desc())
            .limit(10)
            .all()
        )

        medical_records = (
            db.query(MedicalRecord)
            .filter(MedicalRecord.patient_id == patient.id)
            .order_by(MedicalRecord.created_at.desc())
            .limit(5)
            .all()
        )

        vitals_text = ""
        for v in vitals:
            try:
                date_str = v.recorded_at.strftime('%d.%m.%Y') if v.recorded_at else '?'
            except Exception:
                date_str = '?'
            vitals_text += (
                f"- {v.vital_type}: {v.value} {VITAL_UNITS.get(v.vital_type, '')} "
                f"({date_str})\n"
            )

        records_text = ""
        for r in medical_records:
            records_text += (
                f"- Tip: {r.record_type}, "
                f"Diagnostic: {getattr(r, 'diagnosis', '') or 'N/A'}, "
                f"Tratament: {getattr(r, 'treatment', '') or 'N/A'}\n"
            )

        age_str = ""
        if patient_user and patient_user.birth_date:
            try:
                birth = patient_user.birth_date
                # Handle both date and datetime (with or without timezone)
                if isinstance(birth, datetime):
                    birth_as_date = birth.date()
                else:
                    birth_as_date = birth
                age = (date.today() - birth_as_date).days // 365
                age_str = f"Vârsta: {age} ani\n"
            except Exception:
                age_str = ""

        chronic = getattr(patient, "chronic_conditions", "") or ""
        allergies = getattr(patient, "allergies", "") or ""

        prompt = f"""Ești un sistem expert medical AI. Analizează datele pacientului și returnează un JSON strict cu evaluarea riscului medical.

DATE PACIENT:
{age_str}Condiții cronice: {chronic or 'Niciuna specificată'}
Alergii: {allergies or 'Niciuna specificată'}

SEMNE VITALE RECENTE:
{vitals_text or 'Nicio măsurătoare disponibilă'}

FIȘE MEDICALE RECENTE:
{records_text or 'Nicio fișă disponibilă'}

Returnează DOAR un JSON valid (fără text înainte sau după):
{{
  "risk_score": <număr întreg 1-10, unde 1=risc minim, 10=risc critic>,
  "risk_level": "<low|medium|high|critical>",
  "main_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "recommendations": ["<rec1>", "<rec2>", "<rec3>"],
  "summary": "<1-2 propoziții rezumat în română>"
}}

Ghid scoruri: 1-3=low, 4-5=medium, 6-7=high, 8-10=critical."""

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json_lib.loads(raw)

    except Exception:
        # Fallback când orice eroare apare — răspuns static bazat pe datele cunoscute
        has_chronic = bool(chronic)
        has_records = len(medical_records) > 0
        fallback_score = 5 if has_chronic else (3 if has_records else 2)
        fallback_level = "medium" if has_chronic else "low"
        result = {
            "risk_score": fallback_score,
            "risk_level": fallback_level,
            "main_factors": (
                [f"Condiții cronice: {chronic}"] if has_chronic else
                (["Date insuficiente pentru evaluare completă"] if not has_records else
                 ["Fișe medicale prezente — evaluare manuală recomandată"])
            ),
            "recommendations": [
                "Consultați medicul pentru o evaluare completă",
                "Monitorizați regulat semnele vitale",
                "Mențineți un stil de viață sănătos",
            ],
            "summary": (
                "Evaluare AI temporar indisponibilă. "
                "Scorul afișat este estimativ bazat pe datele disponibile. "
                "Consultați medicul pentru o evaluare clinică completă."
            ),
        }

    return {
        "patient_id": str(patient_id),
        "risk_score": result.get("risk_score", 5),
        "risk_level": result.get("risk_level", "medium"),
        "main_factors": result.get("main_factors", []),
        "recommendations": result.get("recommendations", []),
        "summary": result.get("summary", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
