from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_doctor_or_admin
from app.models.user import User, UserRole
from app.models.prescription import Prescription
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.prescription_template import PrescriptionTemplate

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


def _enrich(rx: Prescription, db: Session) -> dict:
    doctor = db.query(Doctor).filter(Doctor.id == rx.doctor_id).first()
    doctor_name = None
    if doctor and doctor.user:
        fn = doctor.user.first_name or ""
        ln = doctor.user.last_name or ""
        doctor_name = (fn + " " + ln).strip() or doctor.user.email

    patient = db.query(Patient).filter(Patient.id == rx.patient_id).first()
    patient_name = None
    if patient and patient.user:
        fn = patient.user.first_name or ""
        ln = patient.user.last_name or ""
        patient_name = (fn + " " + ln).strip() or patient.user.email

    return {
        "id": str(rx.id),
        "patient_id": str(rx.patient_id),
        "doctor_id": str(rx.doctor_id),
        "appointment_id": str(rx.appointment_id) if rx.appointment_id else None,
        "medications": rx.medications,
        "notes": rx.notes,
        "issued_at": rx.issued_at.isoformat() if rx.issued_at else None,
        "created_at": rx.created_at.isoformat() if rx.created_at else None,
        "doctor_name": doctor_name,
        "patient_name": patient_name,
    }


@router.post("/")
def create_prescription(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Only doctors can issue prescriptions")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    patient_id = data.get("patient_id")
    medications = data.get("medications", [])
    if not patient_id or not medications:
        raise HTTPException(status_code=400, detail="patient_id and medications are required")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    rx = Prescription(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_id=data.get("appointment_id"),
        medications=medications,
        notes=data.get("notes"),
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)
    return _enrich(rx, db)


@router.get("/my")
def get_my_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []
    rxs = db.query(Prescription).filter(
        Prescription.patient_id == patient.id
    ).order_by(Prescription.issued_at.desc()).all()
    return [_enrich(r, db) for r in rxs]


@router.get("/doctor")
def get_doctor_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(status_code=403, detail="Access denied")
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        return []
    rxs = db.query(Prescription).filter(
        Prescription.doctor_id == doctor.id
    ).order_by(Prescription.issued_at.desc()).all()
    return [_enrich(r, db) for r in rxs]


class TemplateCreate(BaseModel):
    name: str
    medications: list
    notes: Optional[str] = None


@router.get("/templates")
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """Feature 9 — Listează template-urile de rețetă ale doctorului curent."""
    templates = (
        db.query(PrescriptionTemplate)
        .filter(PrescriptionTemplate.doctor_id == current_user.id)
        .order_by(PrescriptionTemplate.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "medications": t.medications,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in templates
    ]


@router.post("/templates")
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """Feature 9 — Salvează un template nou de rețetă."""
    template = PrescriptionTemplate(
        doctor_id=current_user.id,
        name=data.name,
        medications=data.medications,
        notes=data.notes,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"id": str(template.id), "name": template.name}


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """Feature 9 — Șterge un template."""
    t = db.query(PrescriptionTemplate).filter(
        PrescriptionTemplate.id == template_id,
        PrescriptionTemplate.doctor_id == current_user.id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
    return {"message": "Template deleted"}


@router.get("/{prescription_id}/export", response_class=HTMLResponse)
def export_prescription(
    prescription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    # Verifică acces: pacientul propriu sau doctorul care a emis
    patient = db.query(Patient).filter(Patient.id == rx.patient_id).first()
    doctor = db.query(Doctor).filter(Doctor.id == rx.doctor_id).first()
    is_patient_owner = (patient and patient.user_id == current_user.id)
    is_doctor_owner = (doctor and doctor.user_id == current_user.id)
    if not (is_patient_owner or is_doctor_owner):
        raise HTTPException(status_code=403, detail="Access denied")

    enriched = _enrich(rx, db)
    issued = rx.issued_at.strftime("%d.%m.%Y") if rx.issued_at else "-"

    meds_html = ""
    for i, m in enumerate(enriched["medications"], 1):
        meds_html += f"""
        <tr>
          <td>{i}</td>
          <td><strong>{m.get('name', '')}</strong></td>
          <td>{m.get('dose', '')}</td>
          <td>{m.get('frequency', '')}</td>
          <td>{m.get('duration', '')}</td>
          <td>{m.get('notes', '') or '-'}</td>
        </tr>"""

    notes_section = ""
    if enriched["notes"]:
        notes_section = f"<div class='notes'><strong>Observații:</strong> {enriched['notes']}</div>"

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8" />
  <title>Prescripție medicală</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
    .header {{ border-bottom: 2px solid #1976d2; padding-bottom: 16px; margin-bottom: 24px; }}
    .header h1 {{ color: #1976d2; margin: 0 0 8px; font-size: 22px; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin-bottom: 24px; }}
    .info-grid div {{ font-size: 14px; }}
    .info-grid span {{ color: #555; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
    th {{ background: #1976d2; color: #fff; padding: 10px 12px; text-align: left; font-size: 13px; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; }}
    tr:nth-child(even) td {{ background: #f8f9ff; }}
    .notes {{ background: #fff3e0; border-left: 4px solid #ff9800; padding: 12px 16px; border-radius: 4px; font-size: 14px; margin-bottom: 24px; }}
    .footer {{ margin-top: 40px; border-top: 1px solid #eee; padding-top: 16px; font-size: 12px; color: #888; }}
    .signature {{ margin-top: 60px; text-align: right; }}
    @media print {{
      button {{ display: none !important; }}
      body {{ margin: 20px; }}
    }}
    .print-btn {{ background: #1976d2; color: #fff; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; margin-bottom: 20px; }}
  </style>
</head>
<body>
  <button class="print-btn" onclick="window.print()">🖨️ Printează / Salvează PDF</button>

  <div class="header">
    <h1>🏥 MediLink — Prescripție Medicală</h1>
    <p style="margin:0;font-size:14px;color:#555;">Data emiterii: <strong>{issued}</strong></p>
  </div>

  <div class="info-grid">
    <div><span>Pacient:</span> <strong>{enriched['patient_name'] or '-'}</strong></div>
    <div><span>Doctor:</span> <strong>Dr. {enriched['doctor_name'] or '-'}</strong></div>
  </div>

  <h3 style="color:#1976d2;margin-bottom:12px;">Medicamente prescrise</h3>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Medicament</th>
        <th>Doză</th>
        <th>Frecvență</th>
        <th>Durată</th>
        <th>Note</th>
      </tr>
    </thead>
    <tbody>{meds_html}</tbody>
  </table>

  {notes_section}

  <div class="signature">
    <p style="margin:0;font-size:13px;">Semnătura și parafa medicului</p>
    <div style="margin-top:40px;border-top:1px solid #ccc;padding-top:8px;font-size:13px;">
      Dr. {enriched['doctor_name'] or '-'}
    </div>
  </div>

  <div class="footer">
    Generat de MediLink • {datetime.now().strftime('%d.%m.%Y %H:%M')} • Document cu valoare medicală
  </div>

  <script>
    window.onload = function() {{ setTimeout(function() {{ window.print(); }}, 600); }};
  </script>
</body>
</html>"""

    return HTMLResponse(content=html)
