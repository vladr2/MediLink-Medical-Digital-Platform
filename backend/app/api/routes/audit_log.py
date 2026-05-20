from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rbac import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi.responses import StreamingResponse
import csv
import io

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: str
    resource: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


def log_action(
    db: Session,
    user: User,
    action: str,
    resource: str = None,
    details: str = None,
    ip: str = None,
):
    try:
        entry = AuditLog(
            user_id=user.id,
            user_email=user.email,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip,
        )
        db.add(entry)
        db.commit()  # expire_on_commit=False pe SessionLocal — obiectele deja incarcate nu sunt expirate
    except Exception:
        pass  # audit log nu trebuie să blocheze operația principală


@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return logs


@router.get("/export")
def export_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Utilizator", "Actiune", "Resursa", "Detalii", "IP"])

    for log in logs:
        writer.writerow(
            [
                log.created_at.strftime("%d/%m/%Y %H:%M:%S"),
                log.user_email or "",
                log.action or "",
                log.resource or "",
                log.details or "",
                log.ip_address or "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
