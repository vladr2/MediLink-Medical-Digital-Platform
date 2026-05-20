"""
Teste pentru /doctors — managementul doctorilor și relațiile cu pacienții.
Acoperire: GET /, POST /, GET /me, PUT /me, GET /my-patients,
           POST /assign-patient/{id}, GET /{id}.
"""
import uuid
import pytest
from tests.conftest import make_user, make_token, auth
from app.models.user import UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.doctor_patient import DoctorPatient


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_doctor(db, email="doc@test.com", spec="Cardiologie") -> tuple:
    user = make_user(db, email, UserRole.doctor)
    doctor = Doctor(
        id=uuid.uuid4(), user_id=user.id,
        specialization=spec, license_number=f"LIC-{email[:4]}"
    )
    db.add(doctor)
    db.commit()
    token = make_token(user.id)
    return user, doctor, token


def make_patient(db, email="pat@test.com") -> tuple:
    user = make_user(db, email, UserRole.patient)
    patient = Patient(id=uuid.uuid4(), user_id=user.id, blood_type="B+", gender="Feminin")
    db.add(patient)
    db.commit()
    token = make_token(user.id)
    return user, patient, token


# ── TestListDoctors ────────────────────────────────────────────────────────────

class TestListDoctors:
    def test_any_authenticated_user_can_list_doctors(self, client, db, patient_token):
        make_doctor(db)
        r = client.get("/api/doctors/", headers=auth(patient_token))
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_doctor_can_list_all_doctors(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.get("/api/doctors/", headers=auth(doc_token))
        assert r.status_code == 200

    def test_returns_doctor_fields(self, client, db):
        _, _, doc_token = make_doctor(db, spec="Neurologie")
        r = client.get("/api/doctors/", headers=auth(doc_token))
        assert r.status_code == 200
        doctors = r.json()
        assert len(doctors) >= 1
        first = doctors[0]
        assert "specialization" in first
        assert "email" in first

    def test_unauthenticated_cannot_list_doctors(self, client, db):
        r = client.get("/api/doctors/")
        assert r.status_code in (401, 403)

    def test_empty_list_when_no_doctors(self, client, db, patient_token):
        r = client.get("/api/doctors/", headers=auth(patient_token))
        assert r.status_code == 200
        assert r.json() == []


# ── TestGetMyDoctorProfile ────────────────────────────────────────────────────

class TestGetMyDoctorProfile:
    def test_doctor_can_get_own_profile(self, client, db):
        _, doctor, doc_token = make_doctor(db, spec="Pediatrie")
        r = client.get("/api/doctors/me", headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json()["specialization"] == "Pediatrie"

    def test_non_doctor_gets_404(self, client, db, patient_token):
        r = client.get("/api/doctors/me", headers=auth(patient_token))
        assert r.status_code == 404

    def test_doctor_without_profile_gets_404(self, client, db):
        user = make_user(db, "doc_np@test.com", UserRole.doctor)
        token = make_token(user.id)
        r = client.get("/api/doctors/me", headers=auth(token))
        assert r.status_code == 404


# ── TestUpdateDoctorProfile ───────────────────────────────────────────────────

class TestUpdateDoctorProfile:
    def test_doctor_can_update_own_profile(self, client, db):
        _, doctor, doc_token = make_doctor(db)
        r = client.put("/api/doctors/me", json={
            "specialization": "Cardiologie",
            "license_number": doctor.license_number,
            "bio": "Expert în afecțiuni cardiovasculare",
            "department": "Cardiologie",
        }, headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json()["bio"] == "Expert în afecțiuni cardiovasculare"

    def test_patient_cannot_update_doctor_profile(self, client, db, patient_token):
        r = client.put("/api/doctors/me", json={
            "specialization": "Gen",
            "license_number": "HACK-001",
            "bio": "hack",
        }, headers=auth(patient_token))
        assert r.status_code in (404, 403)


# ── TestMyPatients ────────────────────────────────────────────────────────────

class TestMyPatients:
    def test_doctor_gets_empty_list_initially(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.get("/api/doctors/my-patients", headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json() == []

    def test_doctor_sees_assigned_patients(self, client, db):
        _, doctor, doc_token = make_doctor(db)
        _, patient, _ = make_patient(db)
        dp = DoctorPatient(doctor_id=doctor.id, patient_id=patient.id)
        db.add(dp)
        db.commit()
        r = client.get("/api/doctors/my-patients", headers=auth(doc_token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_doctor_does_not_see_other_doctors_patients(self, client, db):
        _, doctor1, doc1_token = make_doctor(db, "d1@test.com")
        _, doctor2, doc2_token = make_doctor(db, "d2@test.com")
        _, patient, _ = make_patient(db)
        dp = DoctorPatient(doctor_id=doctor1.id, patient_id=patient.id)
        db.add(dp)
        db.commit()
        r = client.get("/api/doctors/my-patients", headers=auth(doc2_token))
        assert r.json() == []

    def test_patient_cannot_use_my_patients_endpoint(self, client, db, patient_token):
        r = client.get("/api/doctors/my-patients", headers=auth(patient_token))
        assert r.status_code == 403

    def test_my_patients_contains_patient_fields(self, client, db):
        _, doctor, doc_token = make_doctor(db)
        _, patient, _ = make_patient(db)
        db.add(DoctorPatient(doctor_id=doctor.id, patient_id=patient.id))
        db.commit()
        r = client.get("/api/doctors/my-patients", headers=auth(doc_token))
        assert r.status_code == 200
        p = r.json()[0]
        assert "email" in p
        assert "blood_type" in p


# ── TestAssignPatient ─────────────────────────────────────────────────────────

class TestAssignPatient:
    def test_admin_cannot_assign_patient_to_doctor(self, client, db, admin_token):
        """Admin nu mai are voie să atribuie pacienți — doar asistentul."""
        _, doctor, _ = make_doctor(db)
        _, patient, _ = make_patient(db)
        r = client.post(
            f"/api/doctors/assign-patient/{patient.id}?doctor_id={doctor.id}",
            headers=auth(admin_token)
        )
        assert r.status_code == 403

    def test_assistant_can_assign_patient(self, client, db, assistant_token):
        _, doctor, _ = make_doctor(db)
        _, patient, _ = make_patient(db)
        r = client.post(
            f"/api/doctors/assign-patient/{patient.id}?doctor_id={doctor.id}",
            headers=auth(assistant_token)
        )
        assert r.status_code == 200

    def test_patient_cannot_assign_doctor(self, client, db):
        _, doctor, _ = make_doctor(db)
        _, patient, pat_token = make_patient(db)
        r = client.post(
            f"/api/doctors/assign-patient/{patient.id}?doctor_id={doctor.id}",
            headers=auth(pat_token)
        )
        assert r.status_code in (401, 403)

    def test_assign_nonexistent_patient_returns_404(self, client, db, assistant_token):
        _, doctor, _ = make_doctor(db)
        r = client.post(
            f"/api/doctors/assign-patient/{uuid.uuid4()}?doctor_id={doctor.id}",
            headers=auth(assistant_token)
        )
        assert r.status_code == 404

    def test_assign_nonexistent_doctor_returns_404(self, client, db, assistant_token):
        _, patient, _ = make_patient(db)
        r = client.post(
            f"/api/doctors/assign-patient/{patient.id}?doctor_id={uuid.uuid4()}",
            headers=auth(assistant_token)
        )
        assert r.status_code == 404

    def test_assigned_patient_appears_in_my_patients(self, client, db, assistant_token):
        _, doctor, doc_token = make_doctor(db)
        _, patient, _ = make_patient(db)
        client.post(
            f"/api/doctors/assign-patient/{patient.id}?doctor_id={doctor.id}",
            headers=auth(assistant_token)
        )
        r = client.get("/api/doctors/my-patients", headers=auth(doc_token))
        assert len(r.json()) == 1


# ── TestUnassignedPatients ─────────────────────────────────────────────────────

class TestUnassignedPatients:
    def test_get_unassigned_patients(self, client, db, admin_token):
        _, patient, _ = make_patient(db)
        r = client.get("/api/patients/unassigned", headers=auth(admin_token))
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert str(patient.id) in ids

    def test_assigned_patient_not_in_unassigned(self, client, db):
        _, doctor, _ = make_doctor(db)
        _, patient, _ = make_patient(db)
        db.add(DoctorPatient(doctor_id=doctor.id, patient_id=patient.id))
        db.commit()
        admin_user = make_user(db, "adm2@test.com", UserRole.admin)
        admin_tok = make_token(admin_user.id)
        r = client.get("/api/patients/unassigned", headers=auth(admin_tok))
        ids = [p["id"] for p in r.json()]
        assert str(patient.id) not in ids
