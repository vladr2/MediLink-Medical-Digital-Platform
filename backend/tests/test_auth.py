"""
Teste de integrare pentru autentificare: login, register, /me.
"""
import pytest
from tests.conftest import make_user, auth
from app.models.user import UserRole


class TestLogin:
    def test_login_success_returns_tokens(self, client, db):
        make_user(db, "login@test.com", UserRole.patient, password="Test123!")
        resp = client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "Test123!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client, db):
        make_user(db, "user@test.com", UserRole.patient, password="Test123!")
        resp = client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "WrongPassword1!"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "Test123!"
        })
        assert resp.status_code == 401

    def test_login_inactive_user_returns_403(self, client, db):
        from app.models.user import User
        from app.core.security import hash_password
        import uuid
        user = User(
            id=uuid.uuid4(),
            email="inactive@test.com",
            hashed_password=hash_password("Test123!"),
            role=UserRole.patient,
            is_active=False,
        )
        db.add(user)
        db.commit()
        resp = client.post("/api/auth/login", json={
            "email": "inactive@test.com",
            "password": "Test123!"
        })
        assert resp.status_code == 403

    def test_login_missing_fields_returns_422(self, client):
        resp = client.post("/api/auth/login", json={"email": "x@x.com"})
        assert resp.status_code == 422


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@test.com",
            "password": "NewPass123!",
            "role": "patient"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["role"] == "patient"
        assert "id" in data

    def test_register_duplicate_email_returns_400(self, client, db):
        make_user(db, "dup@test.com", UserRole.patient)
        resp = client.post("/api/auth/register", json={
            "email": "dup@test.com",
            "password": "Test123!",
            "role": "patient"
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_register_weak_password_returns_422(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "weak@test.com",
            "password": "abc",
            "role": "patient"
        })
        assert resp.status_code == 422

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "Test123!",
            "role": "patient"
        })
        assert resp.status_code == 422

    def test_register_invalid_role_returns_422(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "test@test.com",
            "password": "Test123!",
            "role": "superuser"
        })
        assert resp.status_code == 422


class TestGetMe:
    def test_get_me_authenticated(self, client, patient_user, patient_token):
        resp = client.get("/api/me", headers=auth(patient_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "patient@test.com"
        assert data["role"] == "patient"

    def test_get_me_no_token_returns_4xx(self, client):
        # HTTPBearer returnează 401 sau 403 când lipsește header-ul Authorization
        resp = client.get("/api/me")
        assert resp.status_code in (401, 403)

    def test_get_me_invalid_token_returns_401(self, client):
        resp = client.get("/api/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_put_me_updates_profile(self, client, patient_user, patient_token):
        resp = client.put("/api/me", headers=auth(patient_token), json={
            "first_name": "Ion",
            "last_name": "Popescu",
            "phone": "0722123456",
        })
        assert resp.status_code == 200

    def test_put_me_response_reflects_changes(self, client, patient_user, patient_token, db):
        client.put("/api/me", headers=auth(patient_token), json={
            "first_name": "Maria",
            "last_name": "Ionescu",
        })
        resp = client.get("/api/me", headers=auth(patient_token))
        data = resp.json()
        assert data["first_name"] == "Maria"
        assert data["last_name"] == "Ionescu"
