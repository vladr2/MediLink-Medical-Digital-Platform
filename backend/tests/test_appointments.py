"""
Teste pentru logica programărilor:
- CRUD de bază
- Logică business: auto-complete past confirmed, blocare completed pe viitor
- RBAC: pacientul poate doar anula
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import auth, make_user, make_token
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.user import UserRole


def make_appointment(db, patient_id, doctor_id, dt: datetime, status=AppointmentStatus.pending):
    """Helper pentru creare programare direct în DB."""
    appt = Appointment(
        id=uuid.uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        datetime=dt,
        status=status,
    )
    db.add(appt)
    db.commit()
    return appt


class TestCreateAppointment:
    def test_patient_can_create_appointment(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        resp = client.post("/api/appointments/", headers=auth(patient_token), json={
            "doctor_id": str(doctor_user.id),
            "datetime": future.isoformat(),
            "notes": "Control de rutină",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["patient_id"] == str(patient_profile.id)

    def test_patient_without_profile_cannot_create(
        self, client, db, patient_user, patient_token, doctor_user
    ):
        """Pacient fără profil de pacient → 404."""
        future = datetime.now(timezone.utc) + timedelta(days=3)
        resp = client.post("/api/appointments/", headers=auth(patient_token), json={
            "doctor_id": str(doctor_user.id),
            "datetime": future.isoformat(),
        })
        assert resp.status_code == 404

    def test_admin_can_create_appointment_for_patient(
        self, client, db, admin_user, admin_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        resp = client.post("/api/appointments/", headers=auth(admin_token), json={
            "patient_id": str(patient_profile.id),
            "doctor_id": str(doctor_user.id),
            "datetime": future.isoformat(),
        })
        assert resp.status_code == 200


class TestListAppointments:
    def test_patient_sees_only_own_appointments(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        make_appointment(db, patient_profile.id, doctor_user.id, future)

        # Creează alt pacient cu programare
        other_user = make_user(db, "other2@test.com", UserRole.patient)
        other_patient = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(other_patient)
        db.commit()
        make_appointment(db, other_patient.id, doctor_user.id, future)

        resp = client.get("/api/appointments/", headers=auth(patient_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["patient_id"] == str(patient_profile.id)

    def test_doctor_sees_only_own_appointments(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        make_appointment(db, patient_profile.id, doctor_user.id, future)

        resp = client.get("/api/appointments/", headers=auth(doctor_token))
        assert resp.status_code == 200
        data = resp.json()
        assert all(a["doctor_id"] == str(doctor_user.id) for a in data)

    def test_admin_sees_all_appointments(
        self, client, db, admin_user, admin_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        make_appointment(db, patient_profile.id, doctor_user.id, future)
        make_appointment(db, patient_profile.id, doctor_user.id, future + timedelta(days=1))

        resp = client.get("/api/appointments/", headers=auth(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestAppointmentStatusLogic:
    """Logica business pentru status-uri programări."""

    def test_auto_complete_past_confirmed_on_list(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        """
        Programările 'confirmed' cu data în trecut trebuie marcate automat
        'completed' când se face GET /appointments/.
        """
        past = datetime.now(timezone.utc) - timedelta(days=2)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, past,
            status=AppointmentStatus.confirmed
        )

        resp = client.get("/api/appointments/", headers=auth(patient_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "completed"

        # Verifică și în DB
        db.refresh(appt)
        assert appt.status == AppointmentStatus.completed

    def test_past_pending_auto_cancelled(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        """
        Programările 'pending' trecute se marchează automat ca 'cancelled'
        (doctorul nu a confirmat la timp).
        """
        past = datetime.now(timezone.utc) - timedelta(days=1)
        make_appointment(
            db, patient_profile.id, doctor_user.id, past,
            status=AppointmentStatus.pending
        )

        resp = client.get("/api/appointments/", headers=auth(patient_token))
        data = resp.json()
        assert data[0]["status"] == "cancelled"

    def test_cannot_complete_future_appointment(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        """
        PATCH cu status=completed pe o programare viitoare → 400.
        Aceasta este logica de business principală.
        """
        future = datetime.now(timezone.utc) + timedelta(days=5)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, future,
            status=AppointmentStatus.confirmed
        )

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(doctor_token),
            json={"status": "completed"}
        )
        assert resp.status_code == 400
        assert "nu a avut loc" in resp.json()["detail"].lower() or \
               "viitor" in resp.json()["detail"].lower() or \
               "finalizat" in resp.json()["detail"].lower()

    def test_can_complete_past_confirmed_appointment(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        """Programare trecută confirmată poate fi marcată completed manual."""
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, past,
            status=AppointmentStatus.confirmed
        )

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(doctor_token),
            json={"status": "completed"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_doctor_can_confirm_appointment(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=3)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, future,
            status=AppointmentStatus.pending
        )

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(doctor_token),
            json={"status": "confirmed"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"


class TestPatientCancelRules:
    def test_patient_can_cancel_own_appointment(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=3)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, future,
            status=AppointmentStatus.pending
        )

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(patient_token),
            json={"status": "cancelled"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_patient_cannot_confirm_appointment(
        self, client, db, patient_user, patient_token, doctor_user, patient_profile
    ):
        future = datetime.now(timezone.utc) + timedelta(days=3)
        appt = make_appointment(
            db, patient_profile.id, doctor_user.id, future
        )

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(patient_token),
            json={"status": "confirmed"}
        )
        assert resp.status_code == 403

    def test_cancelled_by_patient_blocks_further_changes(
        self, client, db, doctor_user, doctor_token, patient_profile
    ):
        """Odată ce pacientul anulează, nimeni nu mai poate modifica programarea."""
        past = datetime.now(timezone.utc) + timedelta(days=1)
        appt = Appointment(
            id=uuid.uuid4(),
            patient_id=patient_profile.id,
            doctor_id=doctor_user.id,
            datetime=past,
            status=AppointmentStatus.cancelled,
            cancelled_by_patient=True,
        )
        db.add(appt)
        db.commit()

        resp = client.patch(
            f"/api/appointments/{appt.id}",
            headers=auth(doctor_token),
            json={"status": "confirmed"}
        )
        assert resp.status_code == 403

    def test_appointment_not_found_returns_404(
        self, client, doctor_user, doctor_token
    ):
        resp = client.patch(
            f"/api/appointments/{uuid.uuid4()}",
            headers=auth(doctor_token),
            json={"status": "confirmed"}
        )
        assert resp.status_code == 404
