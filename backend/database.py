"""
Database layer — SQLite persistence for members and attendance.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "data/members.db")
SAMPLES_DIR = os.environ.get("SAMPLES_DIR", "data/face_samples")


def ensure_dirs():
    """Create required directories."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    if SAMPLES_DIR:
        os.makedirs(SAMPLES_DIR, exist_ok=True)


def init_db():
    """Create tables if they don't exist."""
    ensure_dirs()
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                member_number   INTEGER PRIMARY KEY AUTOINCREMENT,
                membership_id   TEXT UNIQUE NOT NULL DEFAULT '',
                name            TEXT NOT NULL,
                expiration_date TEXT NOT NULL
            )
        """)
        # Trigger: auto-generate membership_id from the new rowid
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS gen_membership_id
            AFTER INSERT ON members
            BEGIN
                UPDATE members
                SET membership_id = 'GYM' || printf('%04d', NEW.member_number)
                WHERE member_number = NEW.member_number;
            END
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                member_number INTEGER NOT NULL,
                membership_id TEXT NOT NULL,
                name          TEXT NOT NULL,
                date          TEXT NOT NULL,
                time          TEXT NOT NULL,
                FOREIGN KEY (member_number) REFERENCES members(member_number)
            )
        """)
        conn.commit()


@contextmanager
def get_db():
    """Yield a database connection with auto-close."""
    uri = DB_PATH.startswith("file:")
    conn = sqlite3.connect(DB_PATH, uri=uri)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Member CRUD ─────────────────────────────────────────────────

def create_member(name: str, expiration_date: str) -> dict:
    """Insert a member — the trigger auto-assigns the GYM-prefixed membership_id."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO members (name, expiration_date) VALUES (?, ?)",
            (name, expiration_date),
        )
        conn.commit()
        member_number = cursor.lastrowid

    return get_member_by_number(member_number)


def get_member(membership_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM members WHERE membership_id = ?", (membership_id,)
        ).fetchone()
    return dict(row) if row else None


def get_member_by_number(member_number: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM members WHERE member_number = ?", (member_number,)
        ).fetchone()
    return dict(row) if row else None


def get_all_members() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM members ORDER BY member_number"
        ).fetchall()
    return [dict(r) for r in rows]


def update_member(membership_id: str, name: str, expiration_date: str) -> Optional[dict]:
    with get_db() as conn:
        conn.execute(
            "UPDATE members SET name = ?, expiration_date = ? WHERE membership_id = ?",
            (name, expiration_date, membership_id),
        )
        conn.commit()
    return get_member(membership_id)


def delete_member(membership_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM members WHERE membership_id = ?", (membership_id,)
        )
        conn.commit()
    return cursor.rowcount > 0


# ── Attendance ──────────────────────────────────────────────────

def log_attendance(membership_id: str, name: str) -> dict:
    member = get_member(membership_id)
    member_number = member["member_number"] if member else 0
    now = datetime.now()
    record = {
        "member_number": member_number,
        "membership_id": membership_id,
        "name": name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
    }
    with get_db() as conn:
        conn.execute(
            "INSERT INTO attendance (member_number, membership_id, name, date, time) VALUES (?, ?, ?, ?, ?)",
            (record["member_number"], record["membership_id"], record["name"], record["date"], record["time"]),
        )
        conn.commit()
    return record


def get_attendance(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM attendance ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
