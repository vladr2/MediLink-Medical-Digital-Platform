import hashlib
import pyotp
import secrets as _secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    MfaVerifyRequest, MfaEnableRequest, MfaDisableRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.api.routes.audit_log import log_action
from app.middleware.auth import get_current_user
from pydantic import BaseModel


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(key_func=get_remote_address)


# ── Utilități ─────────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    """SHA-256 al refresh token-ului — nu stocăm token plain text."""
    return hashlib.sha256(token.encode()).hexdigest()


def _parse_user_agent(ua: str) -> str:
    """Transformă un User-Agent string în formă lizibilă: 'Chrome (Windows)'."""
    if not ua:
        return "Dispozitiv necunoscut"
    lower = ua.lower()

    browser = "Browser"
    if "edg/" in lower or "edgios" in lower or "edga/" in lower:
        browser = "Edge"
    elif "firefox" in lower:
        browser = "Firefox"
    elif "chrome" in lower:
        browser = "Chrome"
    elif "safari" in lower:
        browser = "Safari"
    elif "curl" in lower or "python" in lower or "httpie" in lower:
        browser = "Client API"

    os_name = ""
    if "android" in lower:
        os_name = "Android"
    elif "iphone" in lower:
        os_name = "iPhone"
    elif "ipad" in lower:
        os_name = "iPad"
    elif "windows" in lower:
        os_name = "Windows"
    elif "mac os" in lower or "macintosh" in lower:
        os_name = "macOS"
    elif "linux" in lower:
        os_name = "Linux"

    return f"{browser} ({os_name})" if os_name else browser


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )

    # ── 2FA: dacă userul are MFA activat, returnează un token temporar ──────
    if user.mfa_secret:
        mfa_token = create_access_token(
            {"sub": str(user.id), "type": "mfa_pending"},
            expires_delta=timedelta(minutes=5),
        )
        return TokenResponse(mfa_required=True, mfa_token=mfa_token)

    # ── Login normal (fără MFA) ─────────────────────────────────────────────
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Curăță sesiunile expirate sau în exces
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.last_activity < cutoff,
    ).delete(synchronize_session=False)

    MAX_SESSIONS = 5
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.is_active == True)
        .order_by(UserSession.last_activity.desc())
        .all()
    )
    if len(active_sessions) >= MAX_SESSIONS:
        for old_s in active_sessions[MAX_SESSIONS - 1:]:
            old_s.is_active = False

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=_hash_token(refresh_token),
        device=_parse_user_agent(request.headers.get("user-agent", "")),
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "session_id": str(session.id),
    })

    log_action(db, user, "LOGIN", "auth", "Login reușit", request.client.host if request.client else None)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh")
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    """
    Reîmprospătează access token-ul.
    Validează că refresh token-ul există în DB și sesiunea este activă.
    """
    payload = decode_token(data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Validare sesiune în DB
    token_hash = _hash_token(data.refresh_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash,
        UserSession.is_active == True,
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Session revoked or not found")

    # Actualizează ultima activitate
    session.last_activity = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "session_id": str(session.id),
    })
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    """
    Revocă sesiunea curentă.
    Clientul trimite refresh_token; sesiunea este marcată inactivă.
    """
    token_hash = _hash_token(data.refresh_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash
    ).first()
    if session:
        session.is_active = False
        db.commit()
    return {"message": "Logged out successfully"}


@router.get("/sessions")
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 9 — Listează sesiunile active ale utilizatorului curent.
    Marchează sesiunea curentă cu is_current=True extrasă din JWT.
    """
    # Extrage session_id din access token-ul curent
    auth_header = request.headers.get("Authorization", "")
    current_session_id = None
    if auth_header.startswith("Bearer "):
        payload = decode_token(auth_header[7:])
        if payload:
            current_session_id = payload.get("session_id")

    # Curăță sesiunile expirate înainte de a le lista
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.last_activity < cutoff,
    ).delete(synchronize_session=False)
    db.commit()

    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
        .order_by(UserSession.last_activity.desc())
        .all()
    )

    return [
        {
            "id": str(s.id),
            "device": s.device or "Dispozitiv necunoscut",
            "ip_address": s.ip_address or "IP necunoscut",
            "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "is_current": str(s.id) == current_session_id,
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=200)
def revoke_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 9 — Revocă o sesiune specifică.
    Utilizatorul poate revoca ORICE sesiune a sa (inclusiv cea curentă).
    """
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    db.commit()
    log_action(db, current_user, "REVOKE_SESSION", "auth",
               f"Sesiune revocată: {session.device} / {session.ip_address}")
    return {"message": "Session revoked"}


@router.delete("/sessions", status_code=200)
def revoke_all_other_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Feature 9 — Deconectează toate celelalte sesiuni active.
    Sesiunea curentă (identificată din JWT) rămâne activă.
    """
    auth_header = request.headers.get("Authorization", "")
    current_session_id = None
    if auth_header.startswith("Bearer "):
        payload = decode_token(auth_header[7:])
        if payload:
            current_session_id = payload.get("session_id")

    query = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
    )
    if current_session_id:
        query = query.filter(UserSession.id != current_session_id)

    count = query.count()
    query.update({"is_active": False}, synchronize_session=False)
    db.commit()
    log_action(db, current_user, "REVOKE_ALL_SESSIONS", "auth",
               f"Revocat {count} sesiuni active (exceptând cea curentă)")
    return {"message": f"{count} sessions revoked"}


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    from app.models.patient import Patient
    from app.models.doctor import Doctor

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    db.flush()  # obține user.id fără commit

    # Creează profilul corespunzător rolului
    if data.role == "patient":
        db.add(Patient(user_id=user.id))
    elif data.role == "doctor":
        db.add(Doctor(
            user_id=user.id,
            specialization=data.specialization or "Nespecificat",
            license_number=data.license_number or "N/A",
            department=data.department or "",
        ))

    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schimbă parola utilizatorului curent după verificarea parolei vechi."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Parola curentă este incorectă")

    import re
    p = data.new_password
    if len(p) < 8:
        raise HTTPException(status_code=422, detail="Parola trebuie să aibă minim 8 caractere")
    if not re.search(r"[A-Z]", p):
        raise HTTPException(status_code=422, detail="Parola trebuie să conțină cel puțin o literă mare")
    if not re.search(r"\d", p):
        raise HTTPException(status_code=422, detail="Parola trebuie să conțină cel puțin o cifră")

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    log_action(db, current_user, "CHANGE_PASSWORD", "auth", "Parolă schimbată cu succes")
    return {"message": "Parola a fost schimbată cu succes"}


# ── MFA endpoints ─────────────────────────────────────────────────────────────

@router.post("/mfa/verify", response_model=TokenResponse)
def mfa_verify(data: MfaVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """
    Pasul 2 al login-ului: verifică codul TOTP și returnează tokenurile complete.
    """
    payload = decode_token(data.mfa_token)
    if not payload or payload.get("type") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Token MFA invalid sau expirat")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="Utilizator invalid sau MFA dezactivat")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Cod TOTP invalid sau expirat")

    # Crează sesiune + tokenuri complete (același flow ca login normal)
    refresh_token = create_refresh_token({"sub": str(user.id)})

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.last_activity < cutoff,
    ).delete(synchronize_session=False)

    MAX_SESSIONS = 5
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.is_active == True)
        .order_by(UserSession.last_activity.desc())
        .all()
    )
    if len(active_sessions) >= MAX_SESSIONS:
        for old_s in active_sessions[MAX_SESSIONS - 1:]:
            old_s.is_active = False

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=_hash_token(refresh_token),
        device=_parse_user_agent(request.headers.get("user-agent", "")),
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "session_id": str(session.id),
    })

    log_action(db, user, "LOGIN_MFA", "auth", "Login reușit cu 2FA",
               request.client.host if request.client else None)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/mfa/setup")
def mfa_setup(current_user: User = Depends(get_current_user)):
    """
    Generează un secret TOTP nou. Nu îl salvează încă — userul trebuie să confirme cu un cod.
    Returnează secret-ul și URI-ul otpauth:// pentru QR code.
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="MediLink"
    )
    return {"secret": secret, "qr_uri": qr_uri}


@router.post("/mfa/enable-confirm")
def mfa_enable_confirm(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verifică codul TOTP față de secretul furnizat și activează 2FA.
    Body: {secret: str, code: str}
    """
    secret = data.get("secret", "")
    code = data.get("code", "")
    if not secret or not code:
        raise HTTPException(status_code=400, detail="Secret și cod obligatorii")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Cod TOTP invalid")

    current_user.mfa_secret = secret
    db.commit()
    log_action(db, current_user, "MFA_ENABLED", "auth", "2FA activat")
    return {"message": "2FA activat cu succes"}


@router.post("/mfa/disable")
def mfa_disable(
    data: MfaDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dezactivează 2FA după verificarea codului TOTP curent.
    """
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="2FA nu este activat")

    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Cod TOTP invalid")

    current_user.mfa_secret = None
    db.commit()
    log_action(db, current_user, "MFA_DISABLED", "auth", "2FA dezactivat")
    return {"message": "2FA dezactivat"}
