import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UserSession(Base):
    """
    Feature 9 — Log sesiuni active.
    Stochează refresh token-urile în DB pentru a permite:
    - listarea sesiunilor active (device, IP, ultima activitate)
    - revocarea individuală sau globală a sesiunilor
    - validarea refresh token-urilor la rotire
    """
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # SHA-256 hash al refresh token-ului — nu stocăm token-ul plain
    refresh_token_hash = Column(String, nullable=False, unique=True, index=True)
    # User-Agent parsesat în formă lizibilă: "Chrome (Windows)"
    device = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_activity = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, nullable=False, default=True)
