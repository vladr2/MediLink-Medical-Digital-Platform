"""
Teste pentru RBAC (Role-Based Access Control).
Verifică că fiecare rol are acces doar la endpoint-urile permise.
"""
import pytest
from tests.conftest import auth


class TestAdminOnlyEndpoints:
    """Endpoint-urile admin nu trebuie să fie accesibile de alte roluri."""

    def test_admin_can_list_users(self, client, admin_user, admin_token):
        resp = client.get("/api/users/", headers=auth(admin_token))
        assert resp.status_code == 200

    def test_patient_cannot_list_users(self, client, patient_user, patient_token):
        resp = client.get("/api/users/", headers=auth(patient_token))
        assert resp.status_code == 403

    def test_doctor_cannot_list_users(self, client, doctor_user, doctor_token):
        resp = client.get("/api/users/", headers=auth(doctor_token))
        assert resp.status_code == 403

    def test_assistant_cannot_list_users(self, client, assistant_user, assistant_token):
        resp = client.get("/api/users/", headers=auth(assistant_token))
        assert resp.status_code == 403

    def test_admin_can_access_audit_log(self, client, admin_user, admin_token):
        resp = client.get("/api/audit/", headers=auth(admin_token))
        assert resp.status_code == 200

    def test_patient_cannot_access_audit_log(self, client, patient_user, patient_token):
        resp = client.get("/api/audit/", headers=auth(patient_token))
        assert resp.status_code == 403

    def test_doctor_cannot_access_audit_log(self, client, doctor_user, doctor_token):
        resp = client.get("/api/audit/", headers=auth(doctor_token))
        assert resp.status_code == 403


class TestMedicalStaffEndpoints:
    """Pacienții nu pot accesa lista tuturor pacienților (medical staff only)."""

    def test_doctor_can_list_patients(self, client, doctor_user, doctor_token):
        resp = client.get("/api/patients/", headers=auth(doctor_token))
        assert resp.status_code == 200

    def test_assistant_can_list_patients(self, client, assistant_user, assistant_token):
        resp = client.get("/api/patients/", headers=auth(assistant_token))
        assert resp.status_code == 200

    def test_patient_cannot_list_all_patients(self, client, patient_user, patient_token):
        resp = client.get("/api/patients/", headers=auth(patient_token))
        assert resp.status_code == 403

    def test_admin_can_list_patients(self, client, admin_user, admin_token):
        resp = client.get("/api/patients/", headers=auth(admin_token))
        assert resp.status_code == 200


class TestMedicalRecordsAccess:
    """Doar doctor/admin pot crea și șterge fișe medicale."""

    def test_patient_cannot_create_medical_record(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(patient_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
            "diagnosis": "test",
        })
        assert resp.status_code == 403

    def test_assistant_cannot_create_medical_record(
        self, client, assistant_user, assistant_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(assistant_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
            "diagnosis": "test",
        })
        assert resp.status_code == 403


class TestUnauthenticatedAccess:
    """Niciun endpoint nu trebuie să fie accesibil fără token (401 sau 403)."""

    def test_unauthenticated_get_me(self, client):
        assert client.get("/api/me").status_code in (401, 403)

    def test_unauthenticated_appointments(self, client):
        assert client.get("/api/appointments/").status_code in (401, 403)

    def test_unauthenticated_patients(self, client):
        assert client.get("/api/patients/").status_code in (401, 403)

    def test_unauthenticated_users(self, client):
        assert client.get("/api/users/").status_code in (401, 403)


class TestPatientDataIsolation:
    """Pacientul nu poate accesa datele altor pacienți."""

    def test_patient_can_access_own_profile(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.get("/api/patients/me", headers=auth(patient_token))
        assert resp.status_code == 200

    def test_patient_cannot_access_other_patient_profile(
        self, client, db, patient_token
    ):
        from tests.conftest import make_user
        from app.models.user import UserRole
        from app.models.patient import Patient
        import uuid

        other_user = make_user(db, "other@test.com", UserRole.patient)
        other_patient = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(other_patient)
        db.commit()

        resp = client.get(f"/api/patients/{other_patient.id}", headers=auth(patient_token))
        assert resp.status_code == 403
