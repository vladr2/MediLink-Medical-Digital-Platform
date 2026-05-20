"""
Mesagerie internă doctor ↔ pacient.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from uuid import UUID
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, ConversationSummary
from app.api.routes.notifications import create_notification, get_unread_count, manager
from typing import List

router = APIRouter(prefix="/messages", tags=["messages"])


def _partner_name(user: User) -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or user.email


@router.get("/conversations", response_model=List[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returnează lista conversațiilor (un rând per partener), cu ultimul mesaj și unread count."""
    uid = current_user.id

    # Subquery: toate conversațiile unde userul e sender sau receiver
    all_msgs = (
        db.query(Message)
        .filter(or_(Message.sender_id == uid, Message.receiver_id == uid))
        .order_by(Message.created_at.desc())
        .all()
    )

    # Groupează per partener, ține primul (cel mai recent) mesaj
    seen: dict = {}
    for msg in all_msgs:
        partner_id = msg.receiver_id if msg.sender_id == uid else msg.sender_id
        if partner_id not in seen:
            seen[partner_id] = msg

    conversations = []
    for partner_id, last_msg in seen.items():
        partner = db.query(User).filter(User.id == partner_id).first()
        if not partner:
            continue
        unread = (
            db.query(func.count(Message.id))
            .filter(Message.sender_id == partner_id, Message.receiver_id == uid, Message.is_read == False)
            .scalar() or 0
        )
        prefix = "Dr. " if partner.role == "doctor" else ""
        conversations.append(ConversationSummary(
            partner_id=partner_id,
            partner_name=f"{prefix}{_partner_name(partner)}",
            partner_role=partner.role,
            last_message=last_msg.content[:80] + ("…" if len(last_msg.content) > 80 else ""),
            last_message_at=last_msg.created_at,
            unread_count=unread,
        ))

    # Sortează după ultimul mesaj descrescător
    conversations.sort(key=lambda c: c.last_message_at, reverse=True)
    return conversations


@router.get("/conversation/{partner_id}", response_model=List[MessageResponse])
def get_conversation(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returnează toate mesajele dintre current_user și partner_id, ASC."""
    uid = current_user.id
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == uid, Message.receiver_id == partner_id),
                and_(Message.sender_id == partner_id, Message.receiver_id == uid),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    return messages


@router.post("/read/{partner_id}")
def mark_as_read(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marchează ca citite toate mesajele primite de la partner_id."""
    db.query(Message).filter(
        Message.sender_id == partner_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.get("/unread-count")
def unread_message_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(func.count(Message.id))
        .filter(Message.receiver_id == current_user.id, Message.is_read == False)
        .scalar() or 0
    )
    return {"count": count}


@router.get("/contacts")
def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returnează lista persoanelor cu care userul curent poate iniția o conversație.
    - pacient  → doctorii asignați
    - doctor   → pacienții asignați + ceilalți doctori + asistenți + admini
    - assistant/admin → toți utilizatorii activi
    """
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from app.models.doctor_patient import DoctorPatient

    uid = current_user.id
    contacts = []

    def _user_dict(u: User, role_override: str | None = None):
        return {
            "user_id": str(u.id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "role": role_override or u.role,
        }

    if current_user.role == "patient":
        # Doctorii asignați
        patient = db.query(Patient).filter(Patient.user_id == uid).first()
        if patient:
            assigned = db.query(DoctorPatient).filter(DoctorPatient.patient_id == patient.id).all()
            doctor_ids = [a.doctor_id for a in assigned]
            doctors = db.query(Doctor).filter(Doctor.id.in_(doctor_ids)).all()
            for d in doctors:
                u = db.query(User).filter(User.id == d.user_id, User.is_active == True).first()
                if u:
                    contacts.append(_user_dict(u, "doctor"))

        # Asistenți activi
        assistants = db.query(User).filter(
            User.role == "assistant",
            User.is_active == True,
        ).all()
        for u in assistants:
            contacts.append(_user_dict(u, "assistant"))

        # Alți pacienți activi
        other_patients_users = db.query(User).filter(
            User.role == "patient",
            User.is_active == True,
            User.id != uid,
        ).all()
        for u in other_patients_users:
            contacts.append(_user_dict(u, "patient"))

    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == uid).first()
        if doctor:
            assigned = db.query(DoctorPatient).filter(DoctorPatient.doctor_id == doctor.id).all()
            patient_ids = [a.patient_id for a in assigned]
            patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
            for p in patients:
                u = db.query(User).filter(User.id == p.user_id, User.is_active == True).first()
                if u:
                    contacts.append(_user_dict(u, "patient"))

        # Ceilalți doctori
        other_doctors = db.query(Doctor).filter(Doctor.user_id != uid).all()
        for d in other_doctors:
            u = db.query(User).filter(User.id == d.user_id, User.is_active == True).first()
            if u:
                contacts.append(_user_dict(u, "doctor"))

        # Asistenți și admini
        staff = db.query(User).filter(
            User.role.in_(["assistant", "admin"]),
            User.is_active == True,
        ).all()
        for u in staff:
            contacts.append(_user_dict(u))

    else:  # assistant, admin
        users = db.query(User).filter(User.is_active == True, User.id != uid).all()
        for u in users:
            contacts.append(_user_dict(u))

    return contacts


@router.post("/", response_model=MessageResponse)
def send_message(
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trimite un mesaj și notifică destinatarul prin WebSocket."""
    receiver = db.query(User).filter(User.id == data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Destinatar negăsit")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=data.receiver_id,
        content=data.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Notificare in-app + WebSocket push
    sender_name = _partner_name(current_user)
    prefix = "Dr. " if current_user.role == "doctor" else ""
    notif = create_notification(
        db, data.receiver_id,
        f"Mesaj nou de la {prefix}{sender_name}",
        data.content[:60] + ("…" if len(data.content) > 60 else ""),
        "message",
    )
    unread_notif = get_unread_count(db, data.receiver_id)
    # Număr mesaje necitite pentru destinatar
    unread_msgs = (
        db.query(func.count(Message.id))
        .filter(Message.receiver_id == data.receiver_id, Message.is_read == False)
        .scalar() or 0
    )
    background_tasks.add_task(
        manager.send_to_user,
        str(data.receiver_id),
        {
            "type": "new_message",
            "from_id": str(current_user.id),
            "from_name": f"{prefix}{sender_name}",
            "preview": data.content[:60],
            "unread_count": unread_notif,
            "unread_messages": unread_msgs,
        },
    )

    return msg
