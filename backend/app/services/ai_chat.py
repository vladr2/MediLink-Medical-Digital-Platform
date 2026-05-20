from groq import Groq
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from app.core.config import settings
from app.services.context_builder import (
    build_patient_context,
    build_system_prompt,
    get_available_doctors,
)
from app.models.ai_conversation import AIConversation
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.prescription import Prescription

client = Groq(api_key=settings.GROQ_API_KEY)

INTENT_KEYWORDS = {
    "cardiologie": [
        "inimă",
        "cardiac",
        "chest pain",
        "durere toracică",
        "palpitații",
        "tensiune",
    ],
    "neurologie": ["cap", "migrenă", "amețeală", "convulsii", "neurologice", "memorie"],
    "ortopedie": ["os", "fractură", "articulație", "genunchi", "coloană", "spate"],
    "dermatologie": ["piele", "erupție", "mâncărime", "acnee", "dermatită"],
    "psihiatrie": ["anxietate", "depresie", "somn", "stres", "panică"],
}


def detect_intent(message: str) -> Optional[str]:
    message_lower = message.lower()
    for specialization, keywords in INTENT_KEYWORDS.items():
        if any(kw in message_lower for kw in keywords):
            return specialization
    return None


def chat_with_patient(
    patient_id: UUID,
    message: str,
    conversation_id: Optional[UUID],
    db: Session,
) -> dict:
    context = build_patient_context(patient_id, db)
    system_prompt = build_system_prompt(context)

    if conversation_id:
        conversation = (
            db.query(AIConversation)
            .filter(
                AIConversation.id == conversation_id,
                AIConversation.patient_id == patient_id,
            )
            .first()
        )
    else:
        conversation = None

    if not conversation:
        conversation = AIConversation(patient_id=patient_id, messages=[])
        db.add(conversation)
        db.flush()

    messages = list(conversation.messages or [])
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_prompt}] + messages,
        max_tokens=1000,
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    conversation.messages = messages
    db.commit()
    db.refresh(conversation)

    intent = detect_intent(message)
    suggested_doctor = None

    if intent:
        doctors = get_available_doctors(intent, db)
        if doctors:
            doctor = doctors[0]
            suggested_doctor = {
                "user_id": doctor["user_id"],
                "name": doctor["name"],
                "specialization": doctor["specialization"],
                "department": doctor["department"],
            }

    return {
        "conversation_id": conversation.id,
        "message": assistant_message,
        "intent": intent,
        "suggested_doctor": suggested_doctor,
    }


def generate_medical_summary(patient_id: UUID, db: Session) -> dict:
    """
    Generează un sumar AI al fișei medicale a pacientului folosind Groq LLM.
    Analizează toate înregistrările medicale: diagnostice, tratamente, analize, note.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    generated_at = datetime.now(timezone.utc).isoformat()

    if not patient:
        return {
            "summary": "Pacient negăsit.",
            "generated_at": generated_at,
            "record_count": 0,
        }

    records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )

    if not records:
        return {
            "summary": "Nu există înregistrări medicale pentru a genera un sumar.",
            "generated_at": generated_at,
            "record_count": 0,
        }

    # Construim textul detaliat al istoricului medical
    records_text = ""
    for i, r in enumerate(records, 1):
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else "dată necunoscută"
        records_text += f"\n{i}. [{date_str}] Tip: {r.record_type}\n"
        if r.diagnosis:
            records_text += f"   Diagnostic: {r.diagnosis}\n"
        if r.treatment:
            records_text += f"   Tratament: {r.treatment}\n"
        if r.analysis_result:
            records_text += f"   Rezultat analiză: {r.analysis_result}\n"
        if r.notes_encrypted:
            records_text += f"   Note: {r.notes_encrypted}\n"

    user_prompt = f"""Generează un sumar medical structurat pentru pacientul cu profilul următor:

PROFIL PACIENT:
- Grupă sanguină: {patient.blood_type or "necunoscută"}
- Alergii: {patient.allergies or "niciuna înregistrată"}
- Condiții cronice: {patient.chronic_conditions or "niciuna înregistrată"}

ISTORIC MEDICAL COMPLET ({len(records)} înregistrări):
{records_text}
INSTRUCȚIUNI:
Scrie un sumar medical clar și accesibil care:
1. Prezintă pe scurt profilul medical al pacientului (grupă sanguină, alergii, condiții cronice)
2. Rezumă diagnosticele și tratamentele principale din istoricul medical
3. Evidențiază orice condiții recurente sau cronice observate
4. Menționează cele mai recente intervenții medicale
5. Este structurat cu secțiuni clare, în română
6. NU pune diagnostice noi și NU recomandă tratamente noi

Răspunde DOAR cu sumarul structurat, fără comentarii suplimentare."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ești un asistent medical AI specializat în generarea de sumare medicale "
                    "clare și profesionale pentru pacienți. Răspunzi întotdeauna în română."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=900,
        temperature=0.3,
    )

    summary_text = response.choices[0].message.content

    return {
        "summary": summary_text,
        "generated_at": generated_at,
        "record_count": len(records),
    }


def analyze_review_sentiment(comment: str, rating: int) -> str:
    """
    Feature 14 — Clasifică sentimentul unei recenzii ca 'pozitiv', 'negativ' sau 'neutru'.
    Dacă nu există comentariu, se bazează exclusiv pe rating.
    """
    if not comment or not comment.strip():
        if rating >= 4:
            return "pozitiv"
        elif rating <= 2:
            return "negativ"
        return "neutru"

    prompt = (
        f"Clasifică sentimentul acestei recenzii medicale. "
        f"Rating acordat: {rating}/5. "
        f'Recenzie: "{comment}"\n\n'
        "Răspunde DOAR cu un singur cuvânt: pozitiv, negativ sau neutru."
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0,
        )
        result = response.choices[0].message.content.strip().lower()
        if "negativ" in result:
            return "negativ"
        if "neutru" in result:
            return "neutru"
        return "pozitiv"
    except Exception:
        # Fallback bazat pe rating dacă Groq eșuează
        if rating >= 4:
            return "pozitiv"
        if rating <= 2:
            return "negativ"
        return "neutru"


def generate_patient_report(patient_id: UUID, db: Session, doctor_name: str = "Doctor") -> str:
    """
    Feature 13 — Raport medical AI complet pentru doctor.
    Include: profil pacient, toate fișele medicale, prescripțiile active.
    Returnează HTML gata de tipărit/salvat ca PDF.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return "<html><body><p>Pacient negăsit.</p></body></html>"

    user = patient.user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    generated_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")

    records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc())
        .all()
    )

    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    # ── Construim textul pentru Groq ─────────────────────────────────────────
    records_text = ""
    for i, r in enumerate(records, 1):
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else "?"
        records_text += f"\n{i}. [{date_str}] {r.record_type}"
        if r.diagnosis:
            records_text += f"\n   Diagnostic: {r.diagnosis}"
        if r.treatment:
            records_text += f"\n   Tratament: {r.treatment}"
        if r.analysis_result:
            records_text += f"\n   Analiză: {r.analysis_result}"
        if r.notes_encrypted:
            records_text += f"\n   Note: {r.notes_encrypted}"
        records_text += "\n"

    rx_text = ""
    for i, p in enumerate(prescriptions, 1):
        date_str = p.created_at.strftime("%d.%m.%Y") if p.created_at else "?"
        meds = ", ".join(
            f"{m.get('name','')} {m.get('dose','')} ({m.get('frequency','')})"
            for m in (p.medications or [])
        )
        rx_text += f"\n{i}. [{date_str}] {meds}"
        if p.notes:
            rx_text += f" — {p.notes}"
        rx_text += "\n"

    ai_prompt = f"""Ești un asistent medical AI. Generează un RAPORT CLINIC INTERN pentru medicul {doctor_name}, despre pacientul {full_name}.

PROFIL MEDICAL:
- Grupă sanguină: {patient.blood_type or "necunoscută"}
- Gen: {patient.gender or "nespecificat"}
- Alergii: {patient.allergies or "nicio alergie înregistrată"}
- Condiții cronice: {patient.chronic_conditions or "niciuna"}
- Contact urgență: {patient.emergency_contact or "necompletat"} ({patient.emergency_phone or "-"})

ISTORIC MEDICAL ({len(records)} înregistrări):
{records_text if records_text.strip() else "Nicio înregistrare medicală."}

PRESCRIPȚII ({len(prescriptions)}):
{rx_text if rx_text.strip() else "Nicio prescripție."}

INSTRUCȚIUNI:
Scrie un raport clinic structurat cu:
1. **Rezumat executiv** — starea generală de sănătate în 2-3 propoziții
2. **Diagnostice principale** — lista condițiilor identificate și evoluția lor
3. **Tratamente aplicate** — ce s-a administrat și cu ce efect
4. **Alerte clinice** — alergii, contraindicații, condiții cronice importante
5. **Recomandări** — pași următori propuși (investigații, follow-up, trimiteri)

Ton: profesional medical, în română. NU inventa date care nu există în input."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ești un asistent medical AI care generează rapoarte clinice "
                        "profesionale pentru uz intern medical. Răspunzi în română."
                    ),
                },
                {"role": "user", "content": ai_prompt},
            ],
            max_tokens=1200,
            temperature=0.2,
        )
        ai_assessment = response.choices[0].message.content
    except Exception as e:
        ai_assessment = f"Eroare la generarea evaluării AI: {e}"

    # ── Construim HTML ────────────────────────────────────────────────────────
    def val(v):
        return v if v else "—"

    def fmt_dt(dt):
        if not dt:
            return "—"
        try:
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(dt)

    def fmt_type(t):
        return {"consultatie": "Consultație", "analiza": "Analiză",
                "tratament": "Tratament", "reteta": "Rețetă",
                "investigatie": "Investigație"}.get(str(t), str(t) if t else "—")

    # Tabel fișe
    records_rows = ""
    if records:
        for r in records:
            records_rows += f"""<tr>
              <td>{fmt_dt(r.created_at)}</td>
              <td><span class="badge">{fmt_type(r.record_type)}</span></td>
              <td>{val(r.diagnosis)}</td>
              <td>{val(r.treatment) if r.record_type == "tratament" else val(r.analysis_result)}</td>
              <td style="max-width:200px;word-wrap:break-word">{val(r.notes_encrypted)}</td>
            </tr>"""
    else:
        records_rows = "<tr><td colspan='5' style='text-align:center;color:#888'>Nicio înregistrare</td></tr>"

    # Tabel prescripții
    rx_rows = ""
    if prescriptions:
        for p in prescriptions:
            meds_html = ", ".join(
                f"<strong>{m.get('name','')}</strong> {m.get('dose','')} — {m.get('frequency','')}"
                f"{' (' + m.get('duration','') + ')' if m.get('duration') else ''}"
                for m in (p.medications or [])
            )
            rx_rows += f"""<tr>
              <td>{fmt_dt(p.created_at)}</td>
              <td>{meds_html or "—"}</td>
              <td>{val(p.notes)}</td>
            </tr>"""
    else:
        rx_rows = "<tr><td colspan='3' style='text-align:center;color:#888'>Nicio prescripție</td></tr>"

    # Convertim Markdown bold (**text**) din răspunsul AI în <strong>
    import re as _re
    ai_html = _re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", ai_assessment)
    ai_html = ai_html.replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <title>Raport Medical — {full_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 32px 16px; font-size: 14px; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    .header {{ background: linear-gradient(135deg, #0d47a1, #1565c0); color: white; padding: 28px 32px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; }}
    .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
    .header p {{ opacity: 0.85; font-size: 13px; }}
    .header .badge-confidential {{ background: rgba(255,255,255,.2); border: 1px solid rgba(255,255,255,.4); padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: .5px; }}
    .section {{ background: white; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 16px; overflow: hidden; }}
    .section-title {{ background: #f1f5f9; padding: 12px 20px; font-weight: 700; font-size: 13px; color: #334155; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: .5px; }}
    .section-body {{ padding: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
    .field {{ padding: 10px 14px; background: #f8fafc; border-radius: 8px; border-left: 3px solid #e2e8f0; }}
    .field label {{ font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; display: block; margin-bottom: 3px; }}
    .field span {{ font-size: 13px; color: #1e293b; font-weight: 600; }}
    .field.alert {{ border-left-color: #ef4444; background: #fef2f2; }}
    .field.alert label {{ color: #b91c1c; }}
    .field.alert span {{ color: #991b1b; }}
    .ai-box {{ background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 20px; line-height: 1.75; color: #1e293b; }}
    .ai-box strong {{ color: #0c4a6e; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #f1f5f9; padding: 9px 12px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #64748b; border-bottom: 2px solid #e2e8f0; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    .badge {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 11px; margin-top: 20px; padding-top: 16px; border-top: 1px solid #e2e8f0; }}
    .print-btn {{ display: inline-flex; align-items: center; gap: 8px; background: #0d47a1; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; margin-bottom: 16px; }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .container {{ max-width: 100%; }}
      .header {{ border-radius: 0; margin-bottom: 14px; padding: 18px 24px; print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
      .section {{ box-shadow: none; border: 1px solid #e2e8f0; break-inside: avoid; }}
      .print-btn {{ display: none !important; }}
    }}
  </style>
  <script>window.onload=function(){{setTimeout(function(){{window.print()}},600)}};</script>
</head>
<body>
<div class="container">
  <button class="print-btn" onclick="window.print()">🖨️ Tipărește / Salvează PDF</button>

  <div class="header">
    <div>
      <h1>🏥 Raport Medical Clinic</h1>
      <p>Pacient: <strong>{full_name}</strong> &nbsp;·&nbsp; Generat: {generated_at}</p>
      <p style="margin-top:6px;opacity:.8;">Medic: {doctor_name}</p>
    </div>
    <span class="badge-confidential">🔒 CONFIDENȚIAL</span>
  </div>

  <!-- Profil medical -->
  <div class="section">
    <div class="section-title">🩺 Profil medical</div>
    <div class="section-body">
      <div class="grid">
        <div class="field"><label>Grupă sanguină</label><span>{val(patient.blood_type)}</span></div>
        <div class="field"><label>Gen</label><span>{val(patient.gender)}</span></div>
        <div class="field"><label>Condiții cronice</label><span>{val(patient.chronic_conditions)}</span></div>
        <div class="field {'alert' if patient.allergies else ''}">
          <label>Alergii</label><span>{val(patient.allergies)}</span>
        </div>
        <div class="field"><label>Contact urgență</label><span>{val(patient.emergency_contact)}</span></div>
        <div class="field"><label>Telefon urgență</label><span>{val(patient.emergency_phone)}</span></div>
      </div>
    </div>
  </div>

  <!-- Evaluare AI -->
  <div class="section">
    <div class="section-title">🤖 Evaluare AI — Groq llama-3.3-70b</div>
    <div class="section-body">
      <div class="ai-box">{ai_html}</div>
      <p style="font-size:11px;color:#94a3b8;margin-top:10px;">
        ⚠️ Evaluarea AI are caracter informativ și nu înlocuiește judecata clinică a medicului.
      </p>
    </div>
  </div>

  <!-- Fișe medicale -->
  <div class="section">
    <div class="section-title">📋 Fișe medicale ({len(records)})</div>
    <div class="section-body" style="padding:0">
      <table>
        <thead>
          <tr><th>Data</th><th>Tip</th><th>Diagnostic</th><th>Tratament / Rezultat</th><th>Note</th></tr>
        </thead>
        <tbody>{records_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Prescripții -->
  <div class="section">
    <div class="section-title">💊 Prescripții ({len(prescriptions)})</div>
    <div class="section-body" style="padding:0">
      <table>
        <thead>
          <tr><th>Data</th><th>Medicamente</th><th>Note</th></tr>
        </thead>
        <tbody>{rx_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    MediLink · Raport clinic confidențial · Generat {generated_at} de {doctor_name}
  </div>
</div>
</body>
</html>"""

    return html


def generate_suggested_questions(patient_id: UUID, db: Session) -> list:
    """
    Feature 10 — Generează 3 întrebări personalizate bazate pe istoricul real al pacientului.
    """
    context = build_patient_context(patient_id, db)
    patient = context.get("patient", {})
    records = context.get("recent_records", [])
    prescriptions = context.get("recent_prescriptions", [])

    summary_parts = []
    if patient.get("chronic_conditions"):
        summary_parts.append(f"Condiții cronice: {patient['chronic_conditions']}")
    if patient.get("allergies"):
        summary_parts.append(f"Alergii: {patient['allergies']}")
    for r in records[:3]:
        if r.get("diagnosis"):
            summary_parts.append(f"Diagnostic: {r['diagnosis']} ({r.get('date','')})")
        if r.get("analysis_result"):
            summary_parts.append(f"Analiză: {r['analysis_result']}")
        if r.get("treatment"):
            summary_parts.append(f"Tratament: {r['treatment']}")
    for p in prescriptions[:2]:
        meds = ", ".join(p.get("medications", [])[:2])
        if meds:
            summary_parts.append(f"Medicație: {meds}")

    fallback = [
        "Ce analize am înregistrate recent?",
        "Explică-mi diagnosticul cel mai recent",
        "Ce specialist ar trebui să consult?",
    ]

    if not summary_parts:
        return fallback

    context_text = "\n".join(summary_parts)
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generezi exact 3 întrebări scurte (max 10 cuvinte fiecare) pe care un pacient "
                        "le-ar putea adresa unui asistent medical AI, bazate pe istoricul său medical. "
                        "Fiecare întrebare pe o linie nouă. Fără numerotare, fără prefixe, fără ghilimele."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Istoricul medical al pacientului:\n{context_text}\n\nGenerează 3 întrebări:"
                },
            ],
            max_tokens=120,
            temperature=0.7,
        )
        raw = completion.choices[0].message.content.strip()
        questions = [q.strip(" -•1234567890.)") for q in raw.split("\n") if q.strip()][:3]
        while len(questions) < 3:
            questions.append(fallback[len(questions)])
        return questions
    except Exception:
        return fallback


def detect_analysis_anomalies(record_id: UUID, analysis_result: str, db: Session) -> None:
    """
    Feature 11 — Verifică dacă valorile analizei sunt în afara normalului.
    Rulează în BackgroundTasks după crearea unei înregistrări de tip 'analiza'.
    """
    if not analysis_result or not analysis_result.strip():
        return
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ești un asistent medical. Analizezi rezultate de analize medicale și determini "
                        "dacă există valori în afara intervalului de referință normal. "
                        "Răspunde STRICT în formatul: 'NORMAL' sau 'ANOMALIE: <descriere scurtă, max 120 caractere, în română>'. "
                        "Nu adăuga nimic altceva."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Rezultate analize: {analysis_result}"
                },
            ],
            max_tokens=80,
            temperature=0.0,
        )
        raw = completion.choices[0].message.content.strip()
        has_anomaly = raw.upper().startswith("ANOMALIE")
        anomaly_notes = None
        if has_anomaly:
            parts = raw.split(":", 1)
            anomaly_notes = parts[1].strip() if len(parts) > 1 else "Valori anormale detectate"

        db.query(MedicalRecord).filter(MedicalRecord.id == record_id).update(
            {"has_anomaly": has_anomaly, "anomaly_notes": anomaly_notes},
            synchronize_session=False,
        )
        db.commit()
    except Exception:
        pass
