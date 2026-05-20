import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from app.api.routes import (
    auth,
    users,
    patients,
    appointments,
    medical_records,
    chat,
    doctors,
)
from app.api.routes import audit_log as audit_log_router
from app.api.routes import notifications as notifications_router
from app.api.routes import reviews as reviews_router
from app.api.routes import prescriptions as prescriptions_router
from app.api.routes import video as video_router
from app.api.routes.vitals import router as vitals_router
from app.api.routes.search import router as search_router
from app.api.routes.messages import router as messages_router
from app.api.routes.risk import router as risk_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.reminder_service import send_appointment_reminders

from app.models import (
    user,
    patient,
    medical_record,
    doctor,
    appointment,
    ai_conversation,
    audit_log,
    doctor_patient,
    notification,
    review,
    prescription,
    user_session,
    vital_sign,
    message,
)
from app.middleware.auth import get_current_user
from app.core.database import get_db
from app.schemas.user import UserUpdate

scheduler = AsyncIOScheduler()

# ── Rate limiter (dezactivat în teste) ────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not os.environ.get("TESTING"),
)

app = FastAPI(
    title="MediLink API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(medical_records.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(doctors.router, prefix="/api")
app.include_router(audit_log_router.router, prefix="/api")
app.include_router(notifications_router.router, prefix="/api")
app.include_router(reviews_router.router, prefix="/api")
app.include_router(prescriptions_router.router, prefix="/api")
app.include_router(video_router.router, prefix="/api")
app.include_router(vitals_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(risk_router, prefix="/api")


@app.get("/", tags=["root"])
@app.get("/api", tags=["root"])
def root():
    return {
        "app": "MediLink — o platformă medicală digitală",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
    }


@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(send_appointment_reminders, "interval", minutes=5)
    scheduler.start()


@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "MediLink API"}


def _user_dict(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "birth_date": user.birth_date,
        "address": user.address,
        "email_notifications": user.email_notifications if user.email_notifications is not None else True,
        "mfa_enabled": bool(user.mfa_secret),
    }


@app.get("/api/me")
async def get_me(current_user=Depends(get_current_user)):
    return _user_dict(current_user)


@app.put("/api/me")
async def update_me(
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)
