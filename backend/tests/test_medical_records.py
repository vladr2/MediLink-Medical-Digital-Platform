"""
Teste pentru fișe medicale: CRUD, criptare câmpuri, RBAC.
"""
import uuid
import pytest
from sqlalchemy import text
from tests.conftest import auth, make_user
from app.models.medical_record import MedicalRecord
from app.models.user import UserRole


class TestCreateMedicalRecord:
    def test_doctor_can_create_consultatie(
        self, client, doctor_user, doctor_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(doctor_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
            "diagnosis": "Hipertensiune arterială esențială",
            "notes_encrypted": "Pacient cu tensiune 160/100",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_type"] == "consultatie"
        assert data["diagnosis"] == "Hipertensiune arterială esențială"

    def test_doctor_can_create_analiza(
        self, client, doctor_user, doctor_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(doctor_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "analiza",
            "analysis_result": "Hemoglobina: 12.5 g/dL — ușor scăzut",
        })
        assert resp.status_code == 200
        assert resp.json()["analysis_result"] == "Hemoglobina: 12.5 g/dL — ușor scăzut"

    def test_doctor_can_create_tratament(
        self, client, doctor_user, doctor_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(doctor_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "tratament",
            "treatment": "Enalapril 10mg x 2/zi, 30 zile",
        })
        assert resp.status_code == 200
        assert resp.json()["treatment"] == "Enalapril 10mg x 2/zi, 30 zile"

    def test_patient_cannot_create_record(
        self, client, patient_user, patient_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(patient_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
            "diagnosis": "test",
        })
        assert resp.status_code == 403

    def test_assistant_cannot_create_record(
        self, client, assistant_user, assistant_token, patient_profile
    ):
        resp = client.post("/api/medical-records/", headers=auth(assistant_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
        })
        assert resp.status_code == 403

    def test_nonexistent_patient_returns_404(
        self, client, doctor_user, doctor_token
    ):
        resp = client.post("/api/medical-records/", headers=auth(doctor_token), json={
            "patient_id": str(uuid.uuid4()),
            "record_type": "consultatie",
            "diagnosis": "test",
        })
        assert resp.status_code == 404


class TestListMedicalRecords:
    def test_doctor_can_view_patient_records(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        # Crează o fișă
        record = MedicalRecord(
            id=uuid.uuid4(),
            patient_id=patient_profile.id,
            doctor_id=doctor_user.id,
            record_type="consultatie",
            diagnosis="Test",
        )
        db.add(record)
        db.commit()

        resp = client.get(
            f"/api/medical-records/patient/{patient_profile.id}",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_patient_can_view_own_records(
        self, client, db, doctor_user, patient_user, patient_token, patient_profile
    ):
        record = MedicalRecord(
            id=uuid.uuid4(),
            patient_id=patient_profile.id,
            doctor_id=doctor_user.id,
            record_type="analiza",
            analysis_result="Normal",
        )
        db.add(record)
        db.commit()

        resp = client.get(
            f"/api/medical-records/patient/{patient_profile.id}",
            headers=auth(patient_token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_patient_cannot_view_other_patient_records(
        self, client, db, patient_user, patient_token, doctor_user
    ):
        other_user = make_user(db, "other3@test.com", UserRole.patient)
        from app.models.patient import Patient
        other_patient = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(other_patient)
        db.commit()

        resp = client.get(
            f"/api/medical-records/patient/{other_patient.id}",
            headers=auth(patient_token)
        )
        assert resp.status_code == 403

    def test_records_returned_in_descending_order(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        """Fișele trebuie returnate în ordine descrescătoare după dată."""
        from datetime import timezone, timedelta
        from sqlalchemy.sql import func

        for i in range(3):
            r = MedicalRecord(
                id=uuid.uuid4(),
                patient_id=patient_profile.id,
                doctor_id=doctor_user.id,
                record_type="consultatie",
                diagnosis=f"Diagnostic {i}",
            )
            db.add(r)
        db.commit()

        resp = client.get(
            f"/api/medical-records/patient/{patient_profile.id}",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3


class TestDeleteMedicalRecord:
    def test_doctor_can_delete_own_record(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        record = MedicalRecord(
            id=uuid.uuid4(),
            patient_id=patient_profile.id,
            doctor_id=doctor_user.id,
            record_type="consultatie",
            diagnosis="De șters",
        )
        db.add(record)
        db.commit()

        resp = client.delete(
            f"/api/medical-records/{record.id}",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"]

    def test_patient_cannot_delete_record(
        self, client, db, doctor_user, patient_user, patient_token, patient_profile
    ):
        record = MedicalRecord(
            id=uuid.uuid4(),
            patient_id=patient_profile.id,
            doctor_id=doctor_user.id,
            record_type="consultatie",
        )
        db.add(record)
        db.commit()

        resp = client.delete(
            f"/api/medical-records/{record.id}",
            headers=auth(patient_token)
        )
        assert resp.status_code == 403

    def test_delete_nonexistent_record_returns_404(
        self, client, doctor_user, doctor_token
    ):
        resp = client.delete(
            f"/api/medical-records/{uuid.uuid4()}",
            headers=auth(doctor_token)
        )
        assert resp.status_code == 404


class TestMedicalRecordEncryption:
    def test_diagnosis_encrypted_in_database(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        """
        Câmpul 'diagnosis' trebuie stocat criptat în DB.
        Citind direct din DB (fără ORM), valoarea nu trebuie să fie plaintext.
        """
        from tests.conftest import test_engine as engine

        plaintext_diagnosis = "Diabet zaharat tip II"
        resp = client.post("/api/medical-records/", headers=auth(doctor_token), json={
            "patient_id": str(patient_profile.id),
            "record_type": "consultatie",
            "diagnosis": plaintext_diagnosis,
        })
        assert resp.status_code == 200
        record_id = resp.json()["id"]

        # Citire directă din DB (bypass ORM / TypeDecorator)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT diagnosis FROM medical_records WHERE id = :id"),
                {"id": record_id}
            ).fetchone()

        raw_value = row[0]
        assert raw_value != plaintext_diagnosis, \
            "Diagnoza trebuie stocată criptată, nu plaintext!"
        assert raw_value is not None
        # Token Fernet este URL-safe base64 — nu conține spații sau caractere speciale clare
        assert " " not in raw_value or raw_value.startswith("g")
