"""
Teste pentru profilul de pacient: CRUD, date medicale, export GDPR.
"""
import uuid
import pytest
from tests.conftest import auth, make_user
from app.models.patient import Patient
from app.models.user import UserRole


class TestPatientProfile:
    def test_get_my_patient_profile(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.get("/api/patients/me", headers=auth(patient_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["blood_type"] == "A+"
        assert data["gender"] == "Masculin"
        assert "id" in data

    def test_patient_without_profile_returns_404(
        self, client, patient_user, patient_token
    ):
        """Dacă pacientul nu are profil de pacient → 404."""
        resp = client.get("/api/patients/me", headers=auth(patient_token))
        assert resp.status_code == 404

    def test_doctor_cannot_use_me_endpoint(
        self, client, doctor_user, doctor_token
    ):
        """Doctorul nu are profil de pacient → 404."""
        resp = client.get("/api/patients/me", headers=auth(doctor_token))
        assert resp.status_code == 404

    def test_get_patient_by_id_as_doctor(
        self, client, doctor_user, doctor_token, patient_profile
    ):
        resp = client.get(
            f"/api/patients/{patient_profile.id}",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 200
        assert str(resp.json()["id"]) == str(patient_profile.id)

    def test_get_patient_by_id_as_admin(
        self, client, admin_user, admin_token, patient_profile
    ):
        resp = client.get(
            f"/api/patients/{patient_profile.id}",
            headers=auth(admin_token)
        )
        assert resp.status_code == 200


class TestUpdatePatientProfile:
    def test_patient_can_update_own_profile(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(patient_token),
            json={
                "blood_type": "O+",
                "allergies": "penicilină",
                "gender": "Masculin",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["blood_type"] == "O+"
        assert data["allergies"] == "penicilină"

    def test_update_with_cnp_13_digits(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(patient_token),
            json={"cnp": "1900101123456"}
        )
        assert resp.status_code == 200
        assert resp.json()["cnp"] == "1900101123456"

    def test_update_with_invalid_cnp_returns_422(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(patient_token),
            json={"cnp": "123"}  # prea scurt
        )
        assert resp.status_code == 422

    def test_update_with_invalid_blood_type_returns_422(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(patient_token),
            json={"blood_type": "XY"}
        )
        assert resp.status_code == 422

    def test_patient_cannot_update_other_patient(
        self, client, db, patient_user, patient_token
    ):
        other_user = make_user(db, "other4@test.com", UserRole.patient)
        other_patient = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(other_patient)
        db.commit()

        resp = client.put(
            f"/api/patients/{other_patient.id}",
            headers=auth(patient_token),
            json={"blood_type": "B+"}
        )
        assert resp.status_code == 403

    def test_doctor_can_update_patient_profile(
        self, client, doctor_user, doctor_token, patient_profile
    ):
        """Medicul poate actualiza profilul pacientului."""
        resp = client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(doctor_token),
            json={"blood_type": "AB+", "chronic_conditions": "HTA"}
        )
        assert resp.status_code == 200
        assert resp.json()["blood_type"] == "AB+"

    def test_cnp_is_returned_decrypted_after_update(
        self, client, patient_user, patient_token, patient_profile
    ):
        """CNP-ul returnat de API trebuie să fie plaintext (decriptat)."""
        cnp = "2850203456789"
        client.put(
            f"/api/patients/{patient_profile.id}",
            headers=auth(patient_token),
            json={"cnp": cnp}
        )
        resp = client.get("/api/patients/me", headers=auth(patient_token))
        assert resp.json()["cnp"] == cnp


class TestGdprExport:
    def test_gdpr_export_html_returns_html(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.get(
            "/api/patients/me/export?format=html",
            headers=auth(patient_token)
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        content = resp.text
        assert "MediLink" in content
        assert "GDPR" in content
        assert "Art. 20" in content

    def test_gdpr_export_json_returns_json(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.get(
            "/api/patients/me/export?format=json",
            headers=auth(patient_token)
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = resp.json()
        assert "date_personale" in data
        assert "profil_medical" in data
        assert "programari" in data
        assert "inregistrari_medicale" in data

    def test_gdpr_export_html_contains_patient_name(
        self, client, db, patient_user, patient_token, patient_profile
    ):
        """HTML-ul exportat trebuie să conțină numele pacientului."""
        # Setează numele pacientului
        patient_user.first_name = "Ion"
        patient_user.last_name = "Popescu"
        db.commit()

        resp = client.get(
            "/api/patients/me/export",
            headers=auth(patient_token)
        )
        assert "Ion" in resp.text
        assert "Popescu" in resp.text

    def test_gdpr_export_default_format_is_html(
        self, client, patient_user, patient_token, patient_profile
    ):
        """Fără ?format, default-ul trebuie să fie HTML."""
        resp = client.get(
            "/api/patients/me/export",
            headers=auth(patient_token)
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_non_patient_cannot_export(
        self, client, doctor_user, doctor_token
    ):
        """Doctorul nu are profil de pacient → nu poate exporta."""
        resp = client.get(
            "/api/patients/me/export",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 404

    def test_gdpr_export_json_contains_email(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.get(
            "/api/patients/me/export?format=json",
            headers=auth(patient_token)
        )
        data = resp.json()
        assert data["date_personale"]["Email"] == "patient@test.com"
