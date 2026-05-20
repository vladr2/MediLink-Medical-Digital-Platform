from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, Text
from app.core.config import settings


def get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> str:
    """Criptează un string folosind Fernet (AES-128-CBC + HMAC-SHA256)."""
    if not value:
        return value
    f = get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decriptează un string Fernet. Returnează valoarea originală dacă nu e criptată."""
    if not value:
        return value
    try:
        f = get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Fallback pentru date vechi necriptate (migrare transparentă)
        return value


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator care criptează automat câmpurile sensibile
    la scriere în DB și le decriptează la citire. Câmpul din DB rămâne Text.

    Utilizare: Column(EncryptedString, nullable=True)
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Apelat înainte de INSERT/UPDATE — criptează valoarea."""
        if value is not None and value != "":
            return encrypt(str(value))
        return value

    def process_result_value(self, value, dialect):
        """Apelat după SELECT — decriptează valoarea."""
        if value is not None and value != "":
            return decrypt(value)
        return value
