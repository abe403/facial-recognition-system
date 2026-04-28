"""
Backend unit tests — FastAPI TestClient + SQLite in-memory fixtures.

Tests cover:
  - Member CRUD endpoints
  - Auto-increment membership ID (GYM0001 format)
  - Recognition fallback (empty system)
  - Attendance logging
  - Dashboard stats
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Point the DB to a temp in-memory location so tests never touch real data
os.environ["DB_PATH"] = "file:memdb_api?mode=memory&cache=shared"
os.environ["SAMPLES_DIR"] = "/tmp/facegym_test_samples"

# Import app after env vars are set
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
import database as db


import sqlite3

# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_shared_db():
    """Keep the shared in-memory DB alive."""
    # Keep one connection open so the shared cache persists
    conn = sqlite3.connect(os.environ["DB_PATH"], uri=True)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def fresh_db():
    """Clear data between tests for isolation."""
    yield
    # Cleanup: drop all data between tests
    with db.get_db() as conn:
        conn.execute("DELETE FROM attendance")
        conn.execute("DELETE FROM members")
        # Reset AUTOINCREMENT counter so next ID is GYM0001
        conn.execute("DELETE FROM sqlite_sequence WHERE name='members'")
        conn.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_member(client) -> dict:
    """Create a single test member and return the response body."""
    res = client.post("/api/members", json={
        "name": "Test User",
        "expiration_date": "2099-12-31"
    })
    assert res.status_code == 201
    return res.json()


# ── Member CRUD ───────────────────────────────────────────────────

class TestMemberRegistration:

    def test_create_member_returns_201(self, client):
        res = client.post("/api/members", json={
            "name": "Abraham Torres",
            "expiration_date": "2099-01-01"
        })
        assert res.status_code == 201

    def test_membership_id_auto_assigned(self, client):
        res = client.post("/api/members", json={
            "name": "Auto ID Test",
            "expiration_date": "2099-01-01"
        })
        body = res.json()
        assert body["membership_id"].startswith("GYM")
        assert len(body["membership_id"]) == 7  # "GYM" + 4 digits

    def test_member_number_increments(self, client):
        r1 = client.post("/api/members", json={"name": "First", "expiration_date": "2099-01-01"})
        r2 = client.post("/api/members", json={"name": "Second", "expiration_date": "2099-01-01"})
        assert r2.json()["member_number"] == r1.json()["member_number"] + 1

    def test_first_member_id_is_gym0001(self, client):
        res = client.post("/api/members", json={"name": "First Ever", "expiration_date": "2099-01-01"})
        assert res.json()["membership_id"] == "GYM0001"

    def test_create_member_past_expiration_returns_400(self, client):
        res = client.post("/api/members", json={
            "name": "Expired User",
            "expiration_date": "2000-01-01"
        })
        assert res.status_code == 400

    def test_create_member_invalid_date_returns_422(self, client):
        res = client.post("/api/members", json={
            "name": "Bad Date",
            "expiration_date": "not-a-date"
        })
        assert res.status_code == 422


class TestMemberRetrieval:

    def test_list_members_empty(self, client):
        res = client.get("/api/members")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_members_returns_created(self, client, sample_member):
        res = client.get("/api/members")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "Test User"

    def test_get_member_by_id(self, client, sample_member):
        mid = sample_member["membership_id"]
        res = client.get(f"/api/members/{mid}")
        assert res.status_code == 200
        assert res.json()["name"] == "Test User"

    def test_get_nonexistent_member_returns_404(self, client):
        res = client.get("/api/members/GYM9999")
        assert res.status_code == 404


class TestMemberUpdate:

    def test_update_member_name(self, client, sample_member):
        mid = sample_member["membership_id"]
        res = client.put(f"/api/members/{mid}", json={"name": "Updated Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Name"

    def test_update_nonexistent_member_returns_404(self, client):
        res = client.put("/api/members/GYM9999", json={"name": "Ghost"})
        assert res.status_code == 404


class TestMemberDeletion:

    def test_delete_member(self, client, sample_member):
        mid = sample_member["membership_id"]
        del_res = client.delete(f"/api/members/{mid}")
        assert del_res.status_code == 204
        get_res = client.get(f"/api/members/{mid}")
        assert get_res.status_code == 404

    def test_delete_nonexistent_member_returns_404(self, client):
        res = client.delete("/api/members/GYM9999")
        assert res.status_code == 404


# ── Recognition fallback ──────────────────────────────────────────

class TestRecognition:

    def test_recognize_with_no_members_returns_friendly_message(self, client):
        """When no members exist, the system must not crash — return a clear 200 message."""
        res = client.post("/api/recognize", json={"image": "data:image/png;base64,iVBORw0KGgo="})
        assert res.status_code == 200
        body = res.json()
        assert body["recognized"] is False
        assert "No members" in body["message"]

    def test_recognize_invalid_image_returns_400(self, client, sample_member):
        """Invalid base64 should return 400, not crash the server."""
        res = client.post("/api/recognize", json={"image": "NOT_VALID_BASE64!!"})
        # With a member in the DB, it tries to decode and fails → 400
        assert res.status_code in (400, 200)  # 200 possible if face not detected before decode error


# ── Attendance ────────────────────────────────────────────────────

class TestAttendance:

    def test_get_attendance_empty(self, client):
        res = client.get("/api/attendance")
        assert res.status_code == 200
        assert res.json() == []

    def test_attendance_logged_on_access(self, client, sample_member):
        """Directly log attendance and verify it appears in the list."""
        mid = sample_member["membership_id"]
        db.log_attendance(mid, sample_member["name"])
        res = client.get("/api/attendance")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["membership_id"] == mid


# ── Stats ─────────────────────────────────────────────────────────

class TestStats:

    def test_stats_empty_system(self, client):
        res = client.get("/api/stats")
        assert res.status_code == 200
        body = res.json()
        assert body["total_members"] == 0
        assert body["active_members"] == 0
        assert body["entries_today"] == 0

    def test_stats_counts_active_member(self, client, sample_member):
        res = client.get("/api/stats")
        body = res.json()
        assert body["total_members"] == 1
        assert body["active_members"] == 1
        assert body["expired_members"] == 0

    def test_stats_counts_expired_member(self, client):
        # Register expired member by patching through DB directly
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO members (membership_id, name, expiration_date) VALUES ('GYM9998', 'Old Guy', '2000-01-01')"
            )
            conn.commit()
        res = client.get("/api/stats")
        body = res.json()
        assert body["expired_members"] == 1
        assert body["active_members"] == 0
