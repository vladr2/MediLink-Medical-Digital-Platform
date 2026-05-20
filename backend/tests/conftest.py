"""
Configurare globală pytest pentru MediLink.
Setează variabilele de mediu ÎNAINTE de orice import din app,
astfel încât pydantic-settings să citească valorile de test.
"""
import os
import uuid
from cryptography.fernet import Fernet
from datetime import timedelta

# ── Trebuie setate ÎNAINTE de orice import din app ──────────────────────────
os.environ["DATABASE_URL"] = "postgresql://medilink_user:medilink_pass@db:5432/medilink_test"
os.environ["SECRET_KEY"] = "super-secret-test-key-minimum-32chars!!"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["REDIS_URL"] = "redis://redis:6379"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["TESTING"] = "1"          # dezactivează rate limiter în teste
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import MedicalRecord

TEST_DB_URL = os.environ["DATABASE_URL"]
MAIN_DB_URL = "postgresql://medilink_user:medilink_pass@db:5432/medilink"


# ── Creare bază de date de test (o singură dată) ─────────────────────────────
def _ensure_test_db_exists():
    engine = create_engine(MAIN_DB_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'medilink_test'")
        ).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE medilink_test"))
    engine.dispose()


_ensure_test_db_exists()

# ── Engine și sesiune pentru teste ──────────────────────────────────────────
test_engine = create_engine(TEST_DB_URL, echo=False)
TestingSession = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)

# Recreează schema completă (drop+create) pentru a evita drift față de modele
from sqlalchemy import text as _text
with test_engine.connect() as _conn:
    _conn.execute(_text("DROP SCHEMA public CASCADE"))
    _conn.execute(_text("CREATE SCHEMA public"))
    _conn.execute(_text("GRANT ALL ON SCHEMA public TO medilink_user"))
    _conn.execute(_text("GRANT ALL ON SCHEMA public TO public"))
    _conn.commit()
Base.metadata.create_all(bind=test_engine)


# ── Override get_db cu sesiunea de test ─────────────────────────────────────
def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Curăță tabelele înainte de fiecare test ──────────────────────────────────
@pytest.fixture(autouse=True)
def clean_tables():
    """Golește toate tabelele înainte de fiecare test (TRUNCATE CASCADE)."""
    with test_engine.connect() as conn:
        conn.execute(text("""
            TRUNCATE TABLE
                audit_logs,
                ai_conversations,
                appointments,
                medical_records,
                doctor_patients,
                prescriptions,
                prescription_templates,
                vital_signs,
                notifications,
                patients,
                doctors,
                users
            CASCADE
        """))
        conn.commit()
    yield


# ── Fixture sesiune DB ────────────────────────────────────────────────────────
@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


# ── Fixture TestClient ────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    """Un singur TestClient pentru toată sesiunea — evită probleme cu AsyncIOScheduler."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Helpers ──────────────────────────────────────────────────────────────────
def make_user(db, email: str, role: UserRole, password: str = "Test123!") -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        first_name="Test",
        last_name="User",
    )
    db.add(user)
    db.commit()
    return user


def make_token(user_id) -> str:
    return create_access_token(
        {"sub": str(user_id), "role": "test"},
        expires_delta=timedelta(hours=1),
    )


def auth(token: str) -> dict:
    """Returnează headerele de autentificare Bearer."""
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures utilizatori ──────────────────────────────────────────────────────
@pytest.fixture
def admin_user(db):
    return make_user(db, "admin@test.com", UserRole.admin)


@pytest.fixture
def doctor_user(db):
    user = make_user(db, "doctor@test.com", UserRole.doctor)
    doctor = Doctor(
        id=uuid.uuid4(),
        user_id=user.id,
        specialization="Cardiologie",
        license_number="MED-TEST-001",
    )
    db.add(doctor)
    db.commit()
    return user


@pytest.fixture
def patient_user(db):
    return make_user(db, "patient@test.com", UserRole.patient)


@pytest.fixture
def assistant_user(db):
    return make_user(db, "assistant@test.com", UserRole.assistant)


@pytest.fixture
def patient_profile(db, patient_user):
    patient = Patient(
        id=uuid.uuid4(),
        user_id=patient_user.id,
        blood_type="A+",
        gender="Masculin",
    )
    db.add(patient)
    db.commit()
    return patient


# ── Fixtures tokeni ───────────────────────────────────────────────────────────
@pytest.fixture
def admin_token(admin_user):
    return make_token(admin_user.id)


@pytest.fixture
def doctor_token(doctor_user):
    return make_token(doctor_user.id)


@pytest.fixture
def patient_token(patient_user):
    return make_token(patient_user.id)


@pytest.fixture
def assistant_token(assistant_user):
    return make_token(assistant_user.id)
