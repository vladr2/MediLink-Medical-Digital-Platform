"""
Notificări în timp real (WebSocket) + CRUD simplu.
Importat și de appointments.py pentru create_notification / get_unread_count / manager.
"""
from __future__ import annotations

import asyncio
import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import decode_token
from app.middleware.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── WebSocket connection manager ────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def send_to_user(self, user_id: str, data: dict):
        dead = []
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def send(self, user_id: str, data: dict):
        await self.send_to_user(user_id, data)


manager = ConnectionManager()


# ── Helpers folosiți de appointments.py ────────────────────────────────────
def create_notification(
    db: Session,
    user_id: UUID,
    title: str,
    message: str = "",
    notif_type: str = "info",
) -> Notification:
    notif = Notification(
        user_id=user_id,
        notification_type=notif_type,
        title=title,
        message=message,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_unread_count(db: Session, user_id: UUID) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read == False)
        .count()
    )


# ── WebSocket endpoint ──────────────────────────────────────────────────────
@router.websocket("/ws")
async def notification_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001)
        return

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            await websocket.close(code=4001)
            return
        unread = get_unread_count(db, user.id)
    finally:
        db.close()

    await manager.connect(user_id, websocket)
    try:
        await websocket.send_text(json.dumps({"type": "init", "unread_count": unread}))

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=25)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)


# ── REST endpoints ──────────────────────────────────────────────────────────
@router.get("/", response_model=List[dict])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(n.id),
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"count": get_unread_count(db, current_user.id)}


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False,
    ).update({"read": True})
    db.commit()
    return {"ok": True}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if notif:
        notif.read = True
        db.commit()
    return {"ok": True}
