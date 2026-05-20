"""
Serviciu email pentru notificări MediLink.
Folosește smtplib (stdlib) cu SSL.
Skip silențios dacă SMTP_HOST nu e configurat în .env.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_HOST = os.getenv("SMTP_HOST", "")
_PORT = int(os.getenv("SMTP_PORT", "465"))
_USER = os.getenv("SMTP_USER", "")
_PASS = os.getenv("SMTP_PASS", "")
_FROM = os.getenv("SMTP_FROM", "MediLink <noreply@medilink.ro>")

_CONFIGURED = bool(_HOST and _USER and _PASS)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Trimite email HTML. Returnează True dacă a reușit, False altfel."""
    if not _CONFIGURED:
        logger.debug("SMTP neconfigurat — skip email către %s", to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(_HOST, _PORT, context=ctx) as server:
            server.login(_USER, _PASS)
            server.sendmail(_USER, to, msg.as_string())

        logger.info("Email trimis către %s: %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Eroare trimitere email către %s: %s", to, exc)
        return False


# ── Template-uri HTML ────────────────────────────────────────────────────────

def _base_template(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f8fafd;font-family:Roboto,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafd;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#00a1ff,#0070c9);padding:28px 32px;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:600;letter-spacing:-.3px;">
              🏥 MediLink
            </h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,.8);font-size:13px;">
              Platformă medicală digitală
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            {content}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafd;padding:20px 32px;border-top:1px solid #e4ebf0;">
            <p style="margin:0;color:#94a3b8;font-size:12px;text-align:center;">
              Acest email a fost generat automat de platforma MediLink.<br>
              Dacă nu recunoști această acțiune, te rugăm să contactezi suportul.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _pill(text: str, color: str) -> str:
    return (f'<span style="display:inline-block;padding:4px 12px;border-radius:20px;'
            f'background:{color}20;color:{color};font-size:12px;font-weight:600;">{text}</span>')


def email_new_appointment(doctor_email: str, doctor_name: str,
                          patient_name: str, dt_str: str, reason: str = "") -> None:
    """Notificare doctor: programare nouă solicitată."""
    reason_row = (f'<tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Motiv</td>'
                  f'<td style="padding:6px 0;font-size:13px;font-weight:500;">{reason}</td></tr>'
                  if reason else "")
    content = f"""
      <h2 style="margin:0 0 8px;font-size:18px;color:#111c2d;">Programare nouă solicitată</h2>
      <p style="margin:0 0 24px;color:#64748b;font-size:14px;">
        Ai o nouă solicitare de programare pe platforma MediLink.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#f8fafd;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;width:120px;">Pacient</td>
          <td style="padding:6px 0;font-size:13px;font-weight:500;">{patient_name}</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;">Data și ora</td>
          <td style="padding:6px 0;font-size:13px;font-weight:500;">{dt_str}</td>
        </tr>
        {reason_row}
      </table>
      <p style="margin:0;color:#64748b;font-size:13px;">
        Intră pe platformă pentru a confirma sau respinge această programare.
      </p>
    """
    send_email(
        doctor_email,
        f"[MediLink] Programare nouă — {patient_name}",
        _base_template("Programare nouă — MediLink", content),
    )


def email_appointment_status(patient_email: str, patient_name: str,
                             status: str, dt_str: str) -> None:
    """Notificare pacient: status programare schimbat."""
    status_map = {
        "confirmed": ("Programare confirmată ✅",  "#22c55e", "Programarea ta a fost confirmată de doctor."),
        "cancelled":  ("Programare anulată ❌",     "#ef4444", "Programarea ta a fost anulată."),
        "completed":  ("Consultație finalizată 🎉", "#6366f1", "Consultația ta a fost marcată ca finalizată. Verifică fișa medicală pentru detalii."),
    }
    title_text, color, desc = status_map.get(status, ("Actualizare programare", "#64748b", "Statusul programării tale s-a schimbat."))

    content = f"""
      <h2 style="margin:0 0 8px;font-size:18px;color:#111c2d;">{title_text}</h2>
      <p style="margin:0 0 24px;color:#64748b;font-size:14px;">
        Bună ziua, <strong>{patient_name}</strong>!
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#f8fafd;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;width:120px;">Data și ora</td>
          <td style="padding:6px 0;font-size:13px;font-weight:500;">{dt_str}</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:#64748b;font-size:13px;">Status</td>
          <td style="padding:6px 0;">{_pill(status.upper(), color)}</td>
        </tr>
      </table>
      <p style="margin:0;color:#64748b;font-size:13px;">{desc}</p>
    """
    send_email(
        patient_email,
        f"[MediLink] {title_text}",
        _base_template(title_text, content),
    )
