"""
Teste pentru modulul de securitate: hash parole, JWT tokens.
Teste pure unitare — nu necesită bază de date sau HTTP.
"""
import pytest
import time
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        """Parola hashed nu trebuie să fie în plaintext."""
        pw = "Admin123!"
        hashed = hash_password(pw)
        assert hashed != pw

    def test_hash_starts_with_bcrypt_prefix(self):
        """bcrypt hash-urile încep cu '$2b$'."""
        hashed = hash_password("Test123!")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        """verify_password returnează True pentru parola corectă."""
        pw = "SecurePwd9#"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        """verify_password returnează False pentru parola greșită."""
        hashed = hash_password("Admin123!")
        assert verify_password("WrongPass1!", hashed) is False

    def test_verify_empty_password_false(self):
        """Parola goală nu se potrivește cu niciun hash valid."""
        hashed = hash_password("Admin123!")
        assert verify_password("", hashed) is False

    def test_same_password_different_hashes(self):
        """bcrypt este nedeterminist — același plaintext → hash-uri diferite."""
        pw = "Admin123!"
        assert hash_password(pw) != hash_password(pw)


class TestJWTTokens:
    def test_create_access_token_returns_string(self):
        """create_access_token() returnează un JWT string."""
        token = create_access_token({"sub": "user-id-123"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # header.payload.signature

    def test_decode_valid_token(self):
        """decode_token() returnează payload-ul corect."""
        payload = {"sub": "test-user-id", "role": "doctor"}
        token = create_access_token(payload, expires_delta=timedelta(hours=1))
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test-user-id"
        assert decoded["role"] == "doctor"

    def test_decode_expired_token_returns_none(self):
        """Token expirat → decode_token() returnează None."""
        token = create_access_token({"sub": "uid"}, expires_delta=timedelta(seconds=-1))
        result = decode_token(token)
        assert result is None

    def test_decode_invalid_token_returns_none(self):
        """Token invalid (garbage) → None."""
        assert decode_token("not.a.valid.jwt") is None

    def test_decode_tampered_token_returns_none(self):
        """Token modificat → None (HMAC verification fails)."""
        token = create_access_token({"sub": "uid"})
        parts = token.split(".")
        parts[1] = parts[1] + "tampered"
        tampered = ".".join(parts)
        assert decode_token(tampered) is None

    def test_access_token_has_expiry(self):
        """Token-ul de acces conține câmpul 'exp'."""
        token = create_access_token({"sub": "uid"})
        decoded = decode_token(token)
        assert "exp" in decoded

    def test_access_token_shorter_expiry_than_refresh(self):
        """
        Token-ul de acces expiră înaintea token-ului de refresh.
        access = 15 min, refresh = 7 zile (din settings).
        """
        access = create_access_token({"sub": "uid"})
        refresh = create_refresh_token({"sub": "uid"})
        dec_access = decode_token(access)
        dec_refresh = decode_token(refresh)
        assert dec_access["exp"] < dec_refresh["exp"]

    def test_refresh_token_valid(self):
        """Refresh token creat și decodat corect."""
        token = create_refresh_token({"sub": "user-id"})
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-id"

    def test_custom_expiry_respected(self):
        """timedelta custom este respectat la creare token."""
        token = create_access_token({"sub": "uid"}, expires_delta=timedelta(hours=2))
        decoded = decode_token(token)
        # exp trebuie să fie în aproximativ 2 ore față de acum
        import time
        now = int(time.time())
        assert decoded["exp"] > now + 7000  # cel puțin ~2h
        assert decoded["exp"] < now + 7300  # cel mult ~2h + buffer
