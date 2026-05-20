"""
Teste pentru /prescriptions — rețete medicale și template-uri.
Acoperire: POST /, GET /my, GET /doctor, GET /templates, POST /templates,
           DELETE /templates/{id}, GET /{id}/export.
"""
import uuid
import pytest
from tests.conftest import make_user, make_token, auth
from app.models.user import UserRole
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.prescription import Prescription


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_patient(db, email="pat@test.com") -> tuple:
    user = make_user(db, email, UserRole.patient)
    patient = Patient(id=uuid.uuid4(), user_id=user.id, blood_type="A+", gender="Masculin")
    db.add(patient)
    db.commit()
    token = make_token(user.id)
    return user, patient, token


def make_doctor(db, email="doc@test.com") -> tuple:
    user = make_user(db, email, UserRole.doctor)
    license_number = f"D-{email[:8].replace('@', '-')}"
    doctor = Doctor(id=uuid.uuid4(), user_id=user.id, specialization="Medicină generală", license_number=license_number)
    db.add(doctor)
    db.commit()
    token = make_token(user.id)
    return user, doctor, token


SAMPLE_MEDS = [{"name": "Paracetamol", "dose": "500mg", "frequency": "3x/zi", "duration": "5 zile"}]


def create_prescription(client, doc_token, patient_id):
    return client.post("/api/prescriptions/", json={
        "patient_id": str(patient_id),
        "medications": SAMPLE_MEDS,
        "notes": "Test prescription",
    }, headers=auth(doc_token))


# ── TestCreatePrescription ─────────────────────────────────────────────────────

class TestCreatePrescription:
    def test_doctor_can_create_prescription(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = create_prescription(client, doc_token, patient.id)
        assert r.status_code == 200
        data = r.json()
        assert data["medications"] == SAMPLE_MEDS
        assert data["notes"] == "Test prescription"

    def test_patient_cannot_create_prescription(self, client, db):
        _, patient, pat_token = make_patient(db)
        r = create_prescription(client, pat_token, patient.id)
        assert r.status_code == 403

    def test_assistant_cannot_create_prescription(self, client, db, assistant_token):
        _, patient, _ = make_patient(db)
        r = create_prescription(client, assistant_token, patient.id)
        assert r.status_code == 403

    def test_admin_cannot_create_prescription(self, client, db, admin_token):
        _, patient, _ = make_patient(db)
        r = create_prescription(client, admin_token, patient.id)
        assert r.status_code == 403

    def test_nonexistent_patient_returns_404(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.post("/api/prescriptions/", json={
            "patient_id": str(uuid.uuid4()),
            "medications": SAMPLE_MEDS,
        }, headers=auth(doc_token))
        assert r.status_code == 404

    def test_missing_medications_returns_400(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = client.post("/api/prescriptions/", json={
            "patient_id": str(patient.id),
            "medications": [],
        }, headers=auth(doc_token))
        assert r.status_code == 400

    def test_prescription_contains_patient_and_doctor_names(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = create_prescription(client, doc_token, patient.id)
        assert r.status_code == 200
        data = r.json()
        assert "patient_name" in data
        assert "doctor_name" in data

    def test_unauthenticated_cannot_create(self, client, db):
        r = client.post("/api/prescriptions/", json={
            "patient_id": str(uuid.uuid4()),
            "medications": SAMPLE_MEDS,
        })
        assert r.status_code in (401, 403)


# ── TestGetMyPrescriptions ────────────────────────────────────────────────────

class TestGetMyPrescriptions:
    def test_patient_gets_empty_list_initially(self, client, db):
        _, _, pat_token = make_patient(db)
        r = client.get("/api/prescriptions/my", headers=auth(pat_token))
        assert r.status_code == 200
        assert r.json() == []

    def test_patient_sees_own_prescriptions(self, client, db):
        _, patient, pat_token = make_patient(db)
        _, _, doc_token = make_doctor(db)
        create_prescription(client, doc_token, patient.id)
        r = client.get("/api/prescriptions/my", headers=auth(pat_token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_patient_sees_multiple_prescriptions(self, client, db):
        _, patient, pat_token = make_patient(db)
        _, _, doc_token = make_doctor(db)
        create_prescription(client, doc_token, patient.id)
        create_prescription(client, doc_token, patient.id)
        r = client.get("/api/prescriptions/my", headers=auth(pat_token))
        assert len(r.json()) == 2

    def test_patient_does_not_see_other_patients_prescriptions(self, client, db):
        _, patient1, _ = make_patient(db, "p1@test.com")
        _, patient2, pat2_token = make_patient(db, "p2@test.com")
        _, _, doc_token = make_doctor(db)
        create_prescription(client, doc_token, patient1.id)
        r = client.get("/api/prescriptions/my", headers=auth(pat2_token))
        assert r.json() == []

    def test_user_without_patient_profile_gets_empty_list(self, client, db):
        user = make_user(db, "noprofile@test.com", UserRole.patient)
        token = make_token(user.id)
        r = client.get("/api/prescriptions/my", headers=auth(token))
        assert r.status_code == 200
        assert r.json() == []


# ── TestGetDoctorPrescriptions ────────────────────────────────────────────────

class TestGetDoctorPrescriptions:
    def test_doctor_sees_own_prescriptions(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        create_prescription(client, doc_token, patient.id)
        r = client.get("/api/prescriptions/doctor", headers=auth(doc_token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_doctor_does_not_see_other_doctors_prescriptions(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc1_token = make_doctor(db, "doc1@test.com")
        _, _, doc2_token = make_doctor(db, "doc2@test.com")
        create_prescription(client, doc1_token, patient.id)
        r = client.get("/api/prescriptions/doctor", headers=auth(doc2_token))
        assert r.json() == []

    def test_patient_cannot_use_doctor_endpoint(self, client, db):
        _, _, pat_token = make_patient(db)
        r = client.get("/api/prescriptions/doctor", headers=auth(pat_token))
        assert r.status_code == 403


# ── TestPrescriptionTemplates ─────────────────────────────────────────────────

class TestPrescriptionTemplates:
    def test_doctor_can_create_template(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.post("/api/prescriptions/templates", json={
            "name": "Template gripă",
            "medications": SAMPLE_MEDS,
            "notes": "Standard",
        }, headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json()["name"] == "Template gripă"

    def test_doctor_can_list_templates(self, client, db):
        _, _, doc_token = make_doctor(db)
        client.post("/api/prescriptions/templates", json={
            "name": "T1", "medications": SAMPLE_MEDS
        }, headers=auth(doc_token))
        r = client.get("/api/prescriptions/templates", headers=auth(doc_token))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_empty_templates_initially(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.get("/api/prescriptions/templates", headers=auth(doc_token))
        assert r.status_code == 200
        assert r.json() == []

    def test_doctor_sees_only_own_templates(self, client, db):
        _, _, doc1_token = make_doctor(db, "doc1@test.com")
        _, _, doc2_token = make_doctor(db, "doc2@test.com")
        client.post("/api/prescriptions/templates", json={
            "name": "T1", "medications": SAMPLE_MEDS
        }, headers=auth(doc1_token))
        r = client.get("/api/prescriptions/templates", headers=auth(doc2_token))
        assert r.json() == []

    def test_doctor_can_delete_template(self, client, db):
        _, _, doc_token = make_doctor(db)
        cr = client.post("/api/prescriptions/templates", json={
            "name": "T_del", "medications": SAMPLE_MEDS
        }, headers=auth(doc_token))
        tid = cr.json()["id"]
        r = client.delete(f"/api/prescriptions/templates/{tid}", headers=auth(doc_token))
        assert r.status_code == 200
        r2 = client.get("/api/prescriptions/templates", headers=auth(doc_token))
        assert r2.json() == []

    def test_delete_nonexistent_template_returns_404(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.delete(f"/api/prescriptions/templates/{uuid.uuid4()}", headers=auth(doc_token))
        assert r.status_code == 404

    def test_patient_cannot_create_template(self, client, db):
        _, _, pat_token = make_patient(db)
        r = client.post("/api/prescriptions/templates", json={
            "name": "T", "medications": SAMPLE_MEDS
        }, headers=auth(pat_token))
        assert r.status_code in (401, 403)


# ── TestExportPrescription ────────────────────────────────────────────────────

class TestExportPrescription:
    def _create_and_export(self, client, db, requester_token, patient, doc_token):
        cr = create_prescription(client, doc_token, patient.id)
        rx_id = cr.json()["id"]
        return client.get(f"/api/prescriptions/{rx_id}/export", headers=auth(requester_token))

    def test_doctor_can_export_own_prescription(self, client, db):
        _, patient, _ = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = self._create_and_export(client, db, doc_token, patient, doc_token)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_patient_can_export_own_prescription(self, client, db):
        _, patient, pat_token = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = self._create_and_export(client, db, pat_token, patient, doc_token)
        assert r.status_code == 200
        assert "<html" in r.text.lower()

    def test_exported_html_contains_medication_name(self, client, db):
        _, patient, pat_token = make_patient(db)
        _, _, doc_token = make_doctor(db)
        r = self._create_and_export(client, db, pat_token, patient, doc_token)
        assert "Paracetamol" in r.text

    def test_another_patient_cannot_export_others_prescription(self, client, db):
        _, patient1, _ = make_patient(db, "p1@test.com")
        _, patient2, other_token = make_patient(db, "p2@test.com")
        _, _, doc_token = make_doctor(db)
        cr = create_prescription(client, doc_token, patient1.id)
        rx_id = cr.json()["id"]
        r = client.get(f"/api/prescriptions/{rx_id}/export", headers=auth(other_token))
        assert r.status_code == 403

    def test_export_nonexistent_prescription_returns_404(self, client, db):
        _, _, doc_token = make_doctor(db)
        r = client.get(f"/api/prescriptions/{uuid.uuid4()}/export", headers=auth(doc_token))
        assert r.status_code == 404
