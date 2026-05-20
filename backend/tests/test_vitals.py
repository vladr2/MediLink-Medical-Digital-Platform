"""
Teste pentru /vitals — semne vitale.
Acoperire: GET /my, GET /patient/{id}, POST /, POST /patient/{id}, DELETE /{id}.
"""
import uuid
import pytest
from tests.conftest import make_user, make_token, auth
from app.models.user import UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.vital_sign import VitalSign


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_patient(db, email="p@test.com") -> tuple:
    """Returnează (user, patient, token)."""
    user = make_user(db, email, UserRole.patient)
    patient = Patient(id=uuid.uuid4(), user_id=user.id, blood_type="A+", gender="Masculin")
    db.add(patient)
    db.commit()
    token = make_token(user.id)
    return user, patient, token


def make_doctor(db, email="dr@test.com") -> tuple:
    """Returnează (user, doctor, token)."""
    user = make_user(db, email, UserRole.doctor)
    doctor = Doctor(id=uuid.uuid4(), user_id=user.id, specialization="Cardiologie", license_number=f"X-{email[:8].replace('@','-')}")
    db.add(doctor)
    db.commit()
    token = make_token(user.id)
    return user, doctor, token


def add_vital(db, patient_id, vital_type="pulse", value=72.0) -> VitalSign:
    from datetime import datetime, timezone
    v = VitalSign(
        id=uuid.uuid4(),
        patient_id=patient_id,
        vital_type=vital_type,
        value=value,
        unit="bpm",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(v)
    db.commit()
    return v


# ── TestGetMyVitals ────────────────────────────────────────────────────────────

class TestGetMyVitals:
    def test_patient_gets_empty_list_initially(self, client, db):
        _, _, token = make_patient(db)
        r = client.get("/api/vitals/my", headers=auth(token))
        assert r.status_code == 200
        assert r.json() == []

    def test_patient_gets_own_vitals(self, client, db):
        _, patient, token = make_patient(db)
        add_vital(db, patient.id)
        r = client.get("/api/vitals/my", headers=auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["vital_type"] == "pulse"

    def test_patient_without_profile_gets_404(self, client, db):
        user = make_user(db, "noprofile@test.com", UserRole.patient)
        token = make_token(user.id)
        r = client.get("/api/vitals/my", headers=auth(token))
        assert r.status_code == 404

    def test_unauthenticated_gets_401(self, client, db):
        r = client.get("/api/vitals/my")
        assert r.status_code in (401, 403)


# ── TestGetPatientVitals ───────────────────────────────────────────────────────

class TestGetPatientVitals:
    def test_doctor_can_view_patient_vitals(self, client, db):
        _, patient, _ = make_patient(db)
        add_vital(db, patient.id, value=80.0)
        _, _, doc_token = make_doctor(db)
        r = client.get(f"/api/vitals/patient/{patient.id}", headers=auth(doc_token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_assistant_can_view_patient_vitals(self, client, db, assistant_user, assistant_token):
        _, patient, _ = make_patient(db)
        add_vital(db, patient.id)
        r = client.get(f"/api/vitals/patient/{patient.id}", headers=auth(assistant_token))
        assert r.status_code == 200

    def test_admin_can_view_patient_vitals(self, client, db, admin_token):
        _, patient, _ = make_patient(db)
        add_vital(db, patient.id)
        r = client.get(f"/api/vitals/patient/{patient.id}", headers=auth(admin_token))
        assert r.status_code == 200

    def test_patient_cannot_view_other_patient_vitals(self, client, db):
        _, patient, _ = make_patient(db, "p1@test.com")
        add_vital(db, patient.id)
        _, _, other_token = make_patient(db, "p2@test.com")
        r = client.get(f"/api/vitals/patient/{patient.id}", headers=auth(other_token))
        assert r.status_code == 403

    def test_returns_empty_list_for_patient_with_no_vitals(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = client.get(f"/api/vitals/patient/{patient.id}", headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json() == []


# ── TestAddVital (patient POST /) ─────────────────────────────────────────────

class TestAddVital:
    def test_patient_can_add_vital(self, client, db):
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "pulse", "value": 75.0}, headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["vital_type"] == "pulse"
        assert data["value"] == 75.0
        assert data["unit"] == "bpm"

    def test_patient_can_add_all_vital_types(self, client, db):
        _, _, token = make_patient(db)
        for vital_type, value in [
            ("pulse", 72), ("weight", 75), ("temperature", 36.6),
            ("oxygen_sat", 98), ("blood_pressure_sys", 120), ("blood_pressure_dia", 80),
        ]:
            r = client.post("/api/vitals/", json={"vital_type": vital_type, "value": value}, headers=auth(token))
            assert r.status_code == 200, f"Failed for {vital_type}"

    def test_invalid_vital_type_returns_400(self, client, db):
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "nonexistent", "value": 5.0}, headers=auth(token))
        assert r.status_code == 400

    def test_patient_without_profile_returns_404(self, client, db):
        user = make_user(db, "np2@test.com", UserRole.patient)
        token = make_token(user.id)
        r = client.post("/api/vitals/", json={"vital_type": "pulse", "value": 70.0}, headers=auth(token))
        assert r.status_code == 404

    def test_vital_with_notes(self, client, db):
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={
            "vital_type": "pulse", "value": 80.0, "notes": "după efort"
        }, headers=auth(token))
        assert r.status_code == 200
        assert r.json()["notes"] == "după efort"

    def test_unauthenticated_cannot_add_vital(self, client, db):
        r = client.post("/api/vitals/", json={"vital_type": "pulse", "value": 70.0})
        assert r.status_code in (401, 403)


# ── TestAddVitalForPatient (doctor/assistant POST /patient/{id}) ───────────────

class TestAddVitalForPatient:
    def test_doctor_can_add_vital_for_patient(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = client.post(f"/api/vitals/patient/{patient.id}", json={
            "vital_type": "temperature", "value": 37.2
        }, headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json()["vital_type"] == "temperature"

    def test_assistant_can_add_vital_for_patient(self, client, db, assistant_token):
        _, patient, _ = make_patient(db)
        r = client.post(f"/api/vitals/patient/{patient.id}", json={
            "vital_type": "weight", "value": 80.0
        }, headers=auth(assistant_token))
        assert r.status_code == 200

    def test_patient_cannot_add_vital_for_another_patient(self, client, db):
        _, patient, _ = make_patient(db, "p1@test.com")
        _, _, other_token = make_patient(db, "p2@test.com")
        r = client.post(f"/api/vitals/patient/{patient.id}", json={
            "vital_type": "pulse", "value": 70.0
        }, headers=auth(other_token))
        assert r.status_code == 403

    def test_nonexistent_patient_returns_404(self, client, db):
        _, _, doc_token = make_doctor(db)
        fake_id = uuid.uuid4()
        r = client.post(f"/api/vitals/patient/{fake_id}", json={
            "vital_type": "pulse", "value": 70.0
        }, headers=auth(doc_token))
        assert r.status_code == 404

    def test_response_contains_correct_unit(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = client.post(f"/api/vitals/patient/{patient.id}", json={
            "vital_type": "blood_pressure_sys", "value": 130.0
        }, headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json()["unit"] == "mmHg"


# ── TestDeleteVital ────────────────────────────────────────────────────────────

class TestDeleteVital:
    def test_patient_can_delete_own_vital(self, client, db):
        _, patient, token = make_patient(db)
        vital = add_vital(db, patient.id)
        r = client.delete(f"/api/vitals/{vital.id}", headers=auth(token))
        assert r.status_code == 204

    def test_deleted_vital_no_longer_returned(self, client, db):
        _, patient, token = make_patient(db)
        vital = add_vital(db, patient.id)
        client.delete(f"/api/vitals/{vital.id}", headers=auth(token))
        r = client.get("/api/vitals/my", headers=auth(token))
        assert r.json() == []

    def test_patient_cannot_delete_another_patients_vital(self, client, db):
        _, patient, _ = make_patient(db, "p1@test.com")
        vital = add_vital(db, patient.id)
        _, _, other_token = make_patient(db, "p2@test.com")
        r = client.delete(f"/api/vitals/{vital.id}", headers=auth(other_token))
        assert r.status_code == 404  # not found for that patient

    def test_delete_nonexistent_vital_returns_404(self, client, db):
        _, _, token = make_patient(db)
        r = client.delete(f"/api/vitals/{uuid.uuid4()}", headers=auth(token))
        assert r.status_code == 404


# ── TestVitalAlerts ────────────────────────────────────────────────────────────

class TestVitalAlerts:
    def test_normal_vital_no_alert(self, client, db):
        """Vital normal: 72 bpm — nicio alertă nu trebuie generată."""
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "pulse", "value": 72.0}, headers=auth(token))
        assert r.status_code == 200

    def test_critical_low_pulse_returns_success(self, client, db):
        """Puls critic scăzut (<40) — endpoint returnează success (alerta e async)."""
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "pulse", "value": 30.0}, headers=auth(token))
        assert r.status_code == 200
        assert r.json()["value"] == 30.0

    def test_critical_high_temperature_returns_success(self, client, db):
        """Temperatură critică (>39.5°C) — endpoint returnează success."""
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "temperature", "value": 40.1}, headers=auth(token))
        assert r.status_code == 200

    def test_critical_low_oxygen_sat_returns_success(self, client, db):
        """Saturație critică (<90%) — endpoint returnează success."""
        _, _, token = make_patient(db)
        r = client.post("/api/vitals/", json={"vital_type": "oxygen_sat", "value": 85.0}, headers=auth(token))
        assert r.status_code == 200
