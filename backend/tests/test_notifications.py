"""
Teste pentru /api/notifications — notificări în timp real + CRUD.
Acoperire: GET /, GET /unread-count, PATCH /{id}/read, PATCH /read-all.
"""
import uuid
import pytest
from tests.conftest import make_user, make_token, auth
from app.models.user import UserRole
from app.models.notification import Notification


# ── Helpers ───────────────────────────────────────────────────────────────────

def seed_notification(db, user_id, title="Test", message="Mesaj test",
                      notif_type="info", read=False) -> Notification:
    n = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notif_type,
        read=read,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


# ── TestListNotifications ─────────────────────────────────────────────────────

class TestListNotifications:
    def test_user_gets_empty_list_initially(self, client, db, patient_user, patient_token):
        r = client.get("/api/notifications/", headers=auth(patient_token))
        assert r.status_code == 200
        assert r.json() == []

    def test_user_sees_own_notifications(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, title="Alertă")
        r = client.get("/api/notifications/", headers=auth(patient_token))
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["title"] == "Alertă"

    def test_user_does_not_see_other_users_notifications(self, client, db, patient_token):
        other = make_user(db, "other@test.com", UserRole.patient)
        seed_notification(db, other.id, title="Altcuiva")
        r = client.get("/api/notifications/", headers=auth(patient_token))
        assert r.json() == []

    def test_multiple_notifications_returned(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, title="N1")
        seed_notification(db, patient_user.id, title="N2")
        seed_notification(db, patient_user.id, title="N3")
        r = client.get("/api/notifications/", headers=auth(patient_token))
        assert len(r.json()) == 3

    def test_notification_has_expected_fields(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, title="Test câmpuri", message="Detalii")
        r = client.get("/api/notifications/", headers=auth(patient_token))
        n = r.json()[0]
        assert "id" in n
        assert "title" in n
        assert "message" in n
        assert "type" in n  # API returns 'type', not 'notification_type'
        assert "read" in n

    def test_unauthenticated_cannot_list_notifications(self, client, db):
        r = client.get("/api/notifications/")
        assert r.status_code in (401, 403)


# ── TestNotificationCount ─────────────────────────────────────────────────────

class TestNotificationCount:
    def test_unread_count_zero_initially(self, client, db, patient_user, patient_token):
        r = client.get("/api/notifications/unread-count", headers=auth(patient_token))
        assert r.status_code == 200
        assert r.json().get("count", 0) == 0

    def test_unread_count_increments(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, read=False)
        seed_notification(db, patient_user.id, read=False)
        r = client.get("/api/notifications/unread-count", headers=auth(patient_token))
        assert r.status_code == 200
        assert r.json().get("count", -1) == 2

    def test_read_notifications_not_counted(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, read=True)
        seed_notification(db, patient_user.id, read=False)
        r = client.get("/api/notifications/unread-count", headers=auth(patient_token))
        assert r.json().get("count", -1) == 1


# ── TestMarkAsRead ────────────────────────────────────────────────────────────

class TestMarkAsRead:
    def test_user_can_mark_notification_as_read(self, client, db, patient_user, patient_token):
        n = seed_notification(db, patient_user.id, read=False)
        r = client.patch(f"/api/notifications/{n.id}/read", headers=auth(patient_token))
        assert r.status_code == 200

    def test_notification_is_marked_read_after_patch(self, client, db, patient_user, patient_token):
        n = seed_notification(db, patient_user.id, read=False)
        client.patch(f"/api/notifications/{n.id}/read", headers=auth(patient_token))
        r = client.get("/api/notifications/unread-count", headers=auth(patient_token))
        assert r.json().get("count", -1) == 0

    def test_mark_other_users_notification_silently_ignored(self, client, db, patient_token):
        """Marcarea unei notificări de alt user nu returnează eroare (e silent)."""
        other = make_user(db, "other2@test.com", UserRole.patient)
        n = seed_notification(db, other.id)
        r = client.patch(f"/api/notifications/{n.id}/read", headers=auth(patient_token))
        # API returns 200 silently (query filters by user_id, so no-op for other user's notifs)
        assert r.status_code == 200

    def test_mark_nonexistent_notification_returns_200(self, client, db, patient_token):
        """Notificarea inexistentă: endpoint returnează 200 (no-op silent)."""
        r = client.patch(f"/api/notifications/{uuid.uuid4()}/read", headers=auth(patient_token))
        assert r.status_code == 200


# ── TestMarkAllAsRead ─────────────────────────────────────────────────────────

class TestMarkAllAsRead:
    def test_mark_all_read_clears_unread_count(self, client, db, patient_user, patient_token):
        seed_notification(db, patient_user.id, read=False)
        seed_notification(db, patient_user.id, read=False)
        r = client.patch("/api/notifications/read-all", headers=auth(patient_token))
        assert r.status_code == 200
        count_r = client.get("/api/notifications/unread-count", headers=auth(patient_token))
        assert count_r.json().get("count", -1) == 0

    def test_mark_all_only_affects_own_notifications(self, client, db, patient_token):
        other = make_user(db, "other3@test.com", UserRole.patient)
        other_token = make_token(other.id)
        seed_notification(db, other.id, read=False)
        client.patch("/api/notifications/read-all", headers=auth(patient_token))
        r = client.get("/api/notifications/unread-count", headers=auth(other_token))
        assert r.json().get("count", -1) == 1  # other user's notification untouched
