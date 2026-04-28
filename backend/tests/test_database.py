"""Database-layer unit tests — run independently from the API."""
import os
import pytest

os.environ["DB_PATH"] = "file:memdb_db?mode=memory&cache=shared"
os.environ["SAMPLES_DIR"] = "/tmp/facegym_test_samples"

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db
import sqlite3


@pytest.fixture(scope="session", autouse=True)
def setup_shared_db():
    conn = sqlite3.connect(os.environ["DB_PATH"], uri=True)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def fresh_db():
    yield
    with db.get_db() as conn:
        conn.execute("DELETE FROM attendance")
        conn.execute("DELETE FROM members")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='members'")
        conn.commit()


class TestDatabaseLayer:

    def test_create_member_returns_dict(self):
        m = db.create_member("Juan", "2099-01-01")
        assert isinstance(m, dict)
        assert m["name"] == "Juan"

    def test_membership_id_format(self):
        m = db.create_member("Juan", "2099-01-01")
        assert m["membership_id"] == "GYM0001"

    def test_member_number_autoincrement(self):
        m1 = db.create_member("First", "2099-01-01")
        m2 = db.create_member("Second", "2099-01-01")
        assert m2["member_number"] == m1["member_number"] + 1

    def test_get_member_by_id(self):
        m = db.create_member("Test", "2099-01-01")
        fetched = db.get_member(m["membership_id"])
        assert fetched is not None
        assert fetched["name"] == "Test"

    def test_get_nonexistent_member_returns_none(self):
        assert db.get_member("GYM9999") is None

    def test_get_all_members(self):
        db.create_member("A", "2099-01-01")
        db.create_member("B", "2099-01-01")
        all_m = db.get_all_members()
        assert len(all_m) == 2

    def test_update_member(self):
        m = db.create_member("Old Name", "2099-01-01")
        updated = db.update_member(m["membership_id"], "New Name", "2099-12-31")
        assert updated["name"] == "New Name"

    def test_delete_member(self):
        m = db.create_member("Delete Me", "2099-01-01")
        result = db.delete_member(m["membership_id"])
        assert result is True
        assert db.get_member(m["membership_id"]) is None

    def test_delete_nonexistent_returns_false(self):
        assert db.delete_member("GYM9999") is False

    def test_log_and_retrieve_attendance(self):
        m = db.create_member("Visitor", "2099-01-01")
        db.log_attendance(m["membership_id"], m["name"])
        records = db.get_attendance()
        assert len(records) == 1
        assert records[0]["membership_id"] == m["membership_id"]
