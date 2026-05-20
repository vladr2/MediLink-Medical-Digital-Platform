import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response, HTMLResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timezone
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_medical_staff
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.medical_record import MedicalRecord
from app.models.appointment import Appointment
from app.schemas.patient import PatientCreate, PatientResponse, PatientWithUser
from app.api.routes.audit_log import log_action
from app.services.ai_chat import generate_medical_summary, generate_patient_report

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=List[PatientWithUser])
def list_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    patients = db.query(Patient).join(Patient.user).all()
    result = []
    for p in patients:
        data = PatientWithUser(
            id=p.id,
            user_id=p.user_id,
            blood_type=p.blood_type,
            allergies=p.allergies,
            chronic_conditions=p.chronic_conditions,
            emergency_contact=p.emergency_contact,
            emergency_phone=p.emergency_phone,
            cnp=p.cnp,
            gender=p.gender,
            gdpr_consent_at=p.gdpr_consent_at,
            created_at=p.created_at,
            email=p.user.email,
            is_active=p.user.is_active,
            first_name=p.user.first_name,
            last_name=p.user.last_name,
        )
        result.append(data)
    return result


@router.get("/unassigned", response_model=List[PatientWithUser])
def list_unassigned_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Pacienți fără niciun doctor asignat — pentru dashboard asistent."""
    from app.models.doctor_patient import DoctorPatient
    assigned_patient_ids = db.query(DoctorPatient.patient_id).distinct().subquery()
    patients = (
        db.query(Patient)
        .join(Patient.user)
        .filter(Patient.id.notin_(assigned_patient_ids))
        .all()
    )
    result = []
    for p in patients:
        result.append(PatientWithUser(
            id=p.id, user_id=p.user_id, blood_type=p.blood_type,
            allergies=p.allergies, chronic_conditions=p.chronic_conditions,
            emergency_contact=p.emergency_contact, emergency_phone=p.emergency_phone,
            cnp=p.cnp, gender=p.gender, gdpr_consent_at=p.gdpr_consent_at,
            created_at=p.created_at, email=p.user.email, is_active=p.user.is_active,
            first_name=p.user.first_name, last_name=p.user.last_name,
        ))
    return result


@router.get("/me", response_model=PatientResponse)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    # cnp-ul e decriptat automat de EncryptedString TypeDecorator
    log_action(
        db, current_user, "VIEW_PATIENT_PROFILE", "patients", f"Acces profil propriu"
    )
    return patient


@router.get("/me/ai-summary")
def get_ai_medical_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 7 — Sumar automat fișă medicală (AI).
    Folosește Groq LLM pentru a genera un rezumat structurat al istoricului medical al pacientului.
    """
    if current_user.role != UserRole.patient:
        raise HTTPException(status_code=403, detail="Doar pacienții pot accesa acest endpoint")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Profil pacient negăsit")

    log_action(
        db, current_user, "AI_SUMMARY_GENERATED", "medical_records",
        "Generat sumar AI fișă medicală"
    )
    return generate_medical_summary(patient.id, db)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
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

    # cnp-ul e decriptat automat de EncryptedString TypeDecorator
    log_action(
        db,
        current_user,
        "VIEW_PATIENT",
        "patients",
        f"Acces profil pacient {patient_id}",
    )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: UUID,
    data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == UserRole.patient:
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # TypeDecorator EncryptedString criptează automat la setarea câmpurilor
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    log_action(db, current_user, "UPDATE_PATIENT", "patients",
               f"Actualizat profil pacient {patient_id}")
    return patient


@router.get("/{patient_id}/ai-report", response_class=HTMLResponse)
def get_patient_ai_report(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 13 — Raport medical AI complet pentru doctor.
    Generează cu Groq un raport clinic structurat: profil + fișe + prescripții.
    Returnează HTML cu auto-print (deschis în tab nou).
    Acces: doctor sau admin.
    """
    if current_user.role not in (UserRole.doctor, UserRole.admin):
        raise HTTPException(status_code=403, detail="Acces permis doar medicilor și adminilor")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Pacient negăsit")

    doctor_name = f"Dr. {current_user.first_name or ''} {current_user.last_name or ''}".strip()
    if doctor_name == "Dr.":
        doctor_name = current_user.email

    log_action(
        db, current_user, "AI_REPORT_GENERATED", "patients",
        f"Raport AI generat pentru pacient {patient_id}"
    )
    html = generate_patient_report(patient_id, db, doctor_name)
    return HTMLResponse(content=html)


@router.get("/me/export", summary="Export date personale GDPR (Art. 20)")
def export_my_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    format: str = Query(default="html", description="Format export: html, json sau pdf"),
):
    """
    GDPR Art. 20 — Dreptul la portabilitatea datelor.
    Returnează toate datele personale ale pacientului (HTML lizibil sau JSON tehnic).
    """
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    records = db.query(MedicalRecord).filter(
        MedicalRecord.patient_id == patient.id
    ).order_by(MedicalRecord.created_at.desc()).all()

    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient.id
    ).order_by(Appointment.datetime.desc()).all()

    log_action(db, current_user, "GDPR_EXPORT", "patients",
               "Export date personale GDPR Art. 20")

    generated_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    full_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email

    def fmt_status(s):
        v = s.value if hasattr(s, 'value') else str(s)
        return {"pending": "În așteptare", "confirmed": "Confirmat",
                "completed": "Finalizat", "cancelled": "Anulat"}.get(v, v or "-")

    def fmt_type(t):
        v = t.value if hasattr(t, 'value') else str(t)
        return {"consultatie": "Consultație", "analiza": "Analiză",
                "tratament": "Tratament"}.get(v, v or "-")

    def val(v):
        return v if v else "-"

    def fmt_dt(dt):
        if not dt:
            return "-"
        try:
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(dt)

    is_pdf = format == "pdf"
    if format == "json":
        data = {
            "export_info": {"generat_la": generated_at, "articol_gdpr": "Art. 20 GDPR", "sistem": "MediLink"},
            "date_personale": {
                "Nume complet": full_name, "Email": current_user.email,
                "Telefon": val(current_user.phone), "Data nasterii": val(current_user.birth_date),
                "Adresa": val(current_user.address),
            },
            "profil_medical": {
                "CNP": val(patient.cnp), "Gen": val(patient.gender),
                "Grupa sangvina": val(patient.blood_type), "Alergii": val(patient.allergies),
                "Conditii cronice": val(patient.chronic_conditions),
                "Contact urgenta": val(patient.emergency_contact),
                "Telefon urgenta": val(patient.emergency_phone),
            },
            "inregistrari_medicale": [
                {"Data": fmt_dt(r.created_at), "Tip": fmt_type(r.record_type),
                 "Diagnostic": val(r.diagnosis), "Tratament": val(r.treatment),
                 "Note": val(r.notes_encrypted), "Rezultat analiza": val(r.analysis_result)}
                for r in records
            ],
            "programari": [
                {"Data": fmt_dt(a.datetime), "Status": fmt_status(a.status),
                 "Motiv": val(a.reason), "Note": val(a.notes)}
                for a in appointments
            ],
        }
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=medilink_date_{current_user.email}.json"}
        )

    # ── Format HTML — lizibil pentru pacient ──────────────────────────────────

    def rows_medical():
        if not records:
            return "<tr><td colspan='5' style='text-align:center;color:#888'>Nicio înregistrare medicală</td></tr>"
        out = ""
        for r in records:
            out += f"""<tr>
              <td>{fmt_dt(r.created_at)}</td>
              <td><span class="badge">{fmt_type(r.record_type)}</span></td>
              <td>{val(r.diagnosis)}</td>
              <td>{val(r.treatment) if r.record_type == 'tratament' else val(r.analysis_result)}</td>
              <td>{val(r.notes_encrypted)}</td>
            </tr>"""
        return out

    def rows_appointments():
        if not appointments:
            return "<tr><td colspan='4' style='text-align:center;color:#888'>Nicio programare</td></tr>"
        out = ""
        for a in appointments:
            sv = a.status.value if hasattr(a.status, 'value') else str(a.status)
            status_colors = {
                "pending":   {"bg": "#fffbeb", "color": "#92400e", "border": "#fde68a"},
                "confirmed": {"bg": "#eff6ff", "color": "#1e40af", "border": "#bfdbfe"},
                "completed": {"bg": "#f0fdf4", "color": "#14532d", "border": "#bbf7d0"},
                "cancelled": {"bg": "#fef2f2", "color": "#991b1b", "border": "#fecaca"},
            }
            sc = status_colors.get(sv, {"bg": "#f8fafc", "color": "#475569", "border": "#e2e8f0"})
            dot_color = {"pending": "#f59e0b", "confirmed": "#2563eb",
                         "completed": "#16a34a", "cancelled": "#dc2626"}.get(sv, "#94a3b8")
            status_badge = (
                f'<span style="display:inline-flex;align-items:center;gap:5px;'
                f'padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;'
                f'background:{sc["bg"]};color:{sc["color"]};border:1px solid {sc["border"]};">'
                f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_color};'
                f'flex-shrink:0;display:inline-block;"></span>'
                f'{fmt_status(a.status)}</span>'
            )
            out += f"""<tr>
              <td>{fmt_dt(a.datetime)}</td>
              <td>{status_badge}</td>
              <td>{val(a.reason)}</td>
              <td>{val(a.notes)}</td>
            </tr>"""
        return out

    auto_print_script = "<script>window.onload=function(){{setTimeout(function(){{window.print()}},600)}};</script>" if is_pdf else ""

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fișă medicală — MediLink — {full_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 32px 16px; }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    .header {{ background: linear-gradient(135deg, #1976d2, #0d47a1); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }}
    .header h1 {{ font-size: 24px; margin-bottom: 4px; }}
    .header p {{ opacity: 0.85; font-size: 14px; }}
    .gdpr-notice {{ background: #e3f2fd; border-left: 4px solid #1976d2; padding: 12px 16px; border-radius: 6px; margin-bottom: 24px; font-size: 13px; color: #1565c0; }}
    .section {{ background: white; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 20px; overflow: hidden; }}
    .section-title {{ background: #f1f5f9; padding: 14px 20px; font-weight: 600; font-size: 15px; color: #334155; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 8px; }}
    .section-body {{ padding: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .field {{ padding: 10px 14px; background: #f8fafc; border-radius: 8px; }}
    .field label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; display: block; margin-bottom: 4px; }}
    .field span {{ font-size: 14px; color: #1e293b; font-weight: 500; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #64748b; border-bottom: 2px solid #e2e8f0; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    .badge {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 20px; font-size: 12px; font-weight: 500; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 24px; }}
    .print-btn {{ display: inline-flex; align-items: center; gap: 8px; background: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 20px; }}
    .print-btn:hover {{ background: #1565c0; }}
    @media(max-width:600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .container {{ max-width: 100%; }}
      .header {{ border-radius: 0; margin-bottom: 16px; padding: 20px; print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
      .section {{ box-shadow: none; border: 1px solid #e2e8f0; break-inside: avoid; }}
      .gdpr-notice {{ break-inside: avoid; }}
      .print-btn {{ display: none !important; }}
      a {{ text-decoration: none; }}
    }}
  </style>
  {auto_print_script}
</head>
<body>
<div class="container">
  <button class="print-btn" onclick="window.print()">🖨️ Salvează / Tipărește PDF</button>

  <div class="header">
    <h1>🏥 Fișă medicală — MediLink</h1>
    <p>Document generat la {generated_at} · {full_name}</p>
  </div>

  <div class="gdpr-notice">
    📋 <strong>Conform Art. 20 GDPR</strong> — Dreptul la portabilitatea datelor. Acest document conține toate datele personale și medicale înregistrate în sistemul MediLink.
  </div>

  <div class="section">
    <div class="section-title">👤 Date personale</div>
    <div class="section-body">
      <div class="grid">
        <div class="field"><label>Nume complet</label><span>{full_name}</span></div>
        <div class="field"><label>Adresă email</label><span>{current_user.email}</span></div>
        <div class="field"><label>Telefon</label><span>{val(current_user.phone)}</span></div>
        <div class="field"><label>Data nașterii</label><span>{val(current_user.birth_date)}</span></div>
        <div class="field" style="grid-column:span 2"><label>Adresă</label><span>{val(current_user.address)}</span></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🩺 Profil medical</div>
    <div class="section-body">
      <div class="grid">
        <div class="field"><label>CNP</label><span>{val(patient.cnp)}</span></div>
        <div class="field"><label>Gen</label><span>{val(patient.gender)}</span></div>
        <div class="field"><label>Grupă sanguină</label><span>{val(patient.blood_type)}</span></div>
        <div class="field"><label>Alergii</label><span>{val(patient.allergies)}</span></div>
        <div class="field"><label>Condiții cronice</label><span>{val(patient.chronic_conditions)}</span></div>
        <div class="field"><label>Contact urgență</label><span>{val(patient.emergency_contact)}</span></div>
        <div class="field"><label>Telefon urgență</label><span>{val(patient.emergency_phone)}</span></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📋 Înregistrări medicale ({len(records)})</div>
    <div class="section-body" style="padding:0">
      <table>
        <thead><tr><th>Data</th><th>Tip</th><th>Diagnostic</th><th>Tratament / Rezultat</th><th>Note</th></tr></thead>
        <tbody>{rows_medical()}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📅 Programări ({len(appointments)})</div>
    <div class="section-body" style="padding:0">
      <table>
        <thead><tr><th>Data</th><th>Status</th><th>Motiv</th><th>Note</th></tr></thead>
        <tbody>{rows_appointments()}</tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    MediLink · Export GDPR Art. 20 · {generated_at}
  </div>
</div>
</body>
</html>"""

    if is_pdf:
        return Response(
            content=html,
            media_type="text/html; charset=utf-8",
        )

    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=medilink_date_personale_{current_user.email}.html"
        }
    )
