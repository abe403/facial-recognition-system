"""
Backend unit tests — FastAPI TestClient + SQLite in-memory fixtures.
"""
import os
import sys
import pytest
import sqlite3
from fastapi.testclient import TestClient

# Point the DB to a temp in-memory location so tests never touch real data
os.environ["DB_PATH"] = "file:memdb_api?mode=memory&cache=shared"
os.environ["SAMPLES_DIR"] = "/tmp/facegym_test_samples"

# Import app after env vars are set
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
import database as db
import security

# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_shared_db():
    """Keep the shared in-memory DB alive."""
    conn = sqlite3.connect(os.environ["DB_PATH"], uri=True)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def fresh_db():
    """Clear data between tests for isolation."""
    # Ensure default admin exists for every test
    hashed = security.get_password_hash("admin123")
    db.create_admin("admin", hashed)
    
    yield
    # Cleanup: drop all data between tests
    with db.get_db() as conn:
        conn.execute("DELETE FROM attendance")
        conn.execute("DELETE FROM members")
        conn.execute("DELETE FROM admins")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='members'")
        conn.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Login as admin and return Authorization header."""
    res = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_member(client, auth_headers) -> dict:
    """Create a single test member and return the response body."""
    res = client.post("/api/members", json={
        "name": "Test User",
        "expiration_date": "2099-12-31"
    }, headers=auth_headers)
    assert res.status_code == 201
    return res.json()


# ── Auth ──────────────────────────────────────────────────────────

def test_login_success(client):
    res = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_failure(client):
    res = client.post("/api/auth/login", data={"username": "admin", "password": "wrong-password"})
    assert res.status_code == 401


# ── Member CRUD ───────────────────────────────────────────────────

class TestMemberRegistration:

    def test_create_member_returns_201(self, client, auth_headers):
        res = client.post("/api/members", json={
            "name": "Abraham Torres",
            "expiration_date": "2099-01-01"
        }, headers=auth_headers)
        assert res.status_code == 201

    def test_create_member_unauthorized(self, client):
        res = client.post("/api/members", json={"name": "X", "expiration_date": "2099-01-01"})
        assert res.status_code == 401

    def test_membership_id_auto_assigned(self, client, auth_headers):
        res = client.post("/api/members", json={
            "name": "Auto ID Test",
            "expiration_date": "2099-01-01"
        }, headers=auth_headers)
        body = res.json()
        assert body["membership_id"].startswith("GYM")

    def test_member_number_increments(self, client, auth_headers):
        r1 = client.post("/api/members", json={"name": "First", "expiration_date": "2099-01-01"}, headers=auth_headers)
        r2 = client.post("/api/members", json={"name": "Second", "expiration_date": "2099-01-01"}, headers=auth_headers)
        assert r2.json()["member_number"] == r1.json()["member_number"] + 1


class TestMemberRetrieval:

    def test_list_members_empty(self, client, auth_headers):
        res = client.get("/api/members", headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_list_members_returns_created(self, client, sample_member, auth_headers):
        res = client.get("/api/members", headers=auth_headers)
        assert len(res.json()) == 1

    def test_get_member_by_id(self, client, sample_member, auth_headers):
        mid = sample_member["membership_id"]
        res = client.get(f"/api/members/{mid}", headers=auth_headers)
        assert res.status_code == 200


# ── Recognition (Public) ──────────────────────────────────────────

class TestRecognition:

    def test_recognize_is_public(self, client):
        res = client.post("/api/recognize", json={"image": "data:image/png;base64,iVBORw0KGgo="})
        assert res.status_code == 200


# ── Attendance ────────────────────────────────────────────────────

class TestAttendance:

    def test_get_attendance_unauthorized(self, client):
        res = client.get("/api/attendance")
        assert res.status_code == 401

    def test_get_attendance_authorized(self, client, auth_headers):
        res = client.get("/api/attendance", headers=auth_headers)
        assert res.status_code == 200


# ── Stats ─────────────────────────────────────────────────────────

class TestStats:

    def test_stats_authorized(self, client, auth_headers):
        res = client.get("/api/stats", headers=auth_headers)
        assert res.status_code == 200

    def test_stats_unauthorized(self, client):
        res = client.get("/api/stats")
        assert res.status_code == 401
