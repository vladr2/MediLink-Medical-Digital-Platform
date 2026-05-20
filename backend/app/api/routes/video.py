"""
WebSocket signaling server pentru WebRTC teleconsultație.
Permite max 2 participanți per cameră (appointment_id).
"""
from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient

router = APIRouter(prefix="/video", tags=["video"])

# rooms[appointment_id] = {user_id: websocket}
rooms: Dict[str, Dict[str, WebSocket]] = {}


@router.websocket("/ws/{appointment_id}")
async def video_signaling(
    websocket: WebSocket,
    appointment_id: str,
    token: str = Query(...),
):
    # Acceptă conexiunea întâi (altfel close() nu funcționează corect)
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        # 1. Autentificare
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Autentificare eșuată")
            return
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Token invalid")
            return

        # 2. Verifică user
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4001, reason="User negăsit")
            return

        # 3. Verifică programarea
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        if not appointment:
            await websocket.close(code=4003, reason="Programare negăsită")
            return
        if appointment.status != AppointmentStatus.confirmed:
            await websocket.close(code=4003, reason="Programarea nu este confirmată")
            return

        # 4. Verifică că userul e participant
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        is_patient = patient and str(patient.id) == str(appointment.patient_id)
        is_doctor = str(user.id) == str(appointment.doctor_id)
        if not (is_patient or is_doctor):
            await websocket.close(code=4003, reason="Nu ești participant la această programare")
            return

    finally:
        db.close()

    # 5. Intră în cameră
    room = rooms.setdefault(appointment_id, {})

    if len(room) >= 2 and user_id not in room:
        await websocket.close(code=4003, reason="Camera este plină")
        return

    room[user_id] = websocket
    other_ids = [uid for uid in room if uid != user_id]

    # Notifică celălalt participant
    for other_id in other_ids:
        try:
            await room[other_id].send_text(json.dumps({"type": "peer-joined"}))
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type in ("offer", "answer", "ice-candidate", "ready"):
                for other_id in [uid for uid in room if uid != user_id]:
                    try:
                        await room[other_id].send_text(json.dumps(msg))
                    except Exception:
                        pass

            elif msg_type == "leave":
                break

    except WebSocketDisconnect:
        pass
    finally:
        room.pop(user_id, None)
        for other_id in list(room.keys()):
            try:
                await room[other_id].send_text(json.dumps({"type": "peer-left"}))
            except Exception:
                pass
        if not room:
            rooms.pop(appointment_id, None)
