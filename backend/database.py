"""
Database layer — SQLite persistence for members and attendance.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

# ── Dynamic Config ──────────────────────────────────────────────
# We use properties so that if os.environ changes (e.g. in tests),
# the variables reflect the change immediately without a module reload.

def get_db_path():
    return os.environ.get("DB_PATH", "data/members.db")

def get_samples_dir():
    return os.environ.get("SAMPLES_DIR", "data/face_samples")


def ensure_dirs():
    """Create required directories for the current config."""
    db_path = get_db_path()
    samples_dir = get_samples_dir()
    
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    if samples_dir:
        os.makedirs(samples_dir, exist_ok=True)


def init_db(conn: Optional[sqlite3.Connection] = None):
    """
    Initialize the schema. 
    Can be called with an existing connection or opens a new one.
    """
    if conn is None:
        ensure_dirs()
        with get_db() as c:
            _run_schema_ddl(c)
    else:
        _run_schema_ddl(conn)


def _run_schema_ddl(conn: sqlite3.Connection):
    """Internal: Run the idempotent CREATE TABLE statements."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_number   INTEGER PRIMARY KEY AUTOINCREMENT,
            membership_id   TEXT UNIQUE NOT NULL DEFAULT '',
            name            TEXT NOT NULL,
            expiration_date TEXT NOT NULL
        )
    """)
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
    """
    Yield a database connection with auto-close.
    Self-initializes the schema on every connection to ensure tables exist.
    """
    path = get_db_path()
    uri = path.startswith("file:")
    
    # Ensure directory exists for file-based DBs
    if not uri and os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
    conn = sqlite3.connect(path, uri=uri)
    conn.row_factory = sqlite3.Row
    
    try:
        # Guarantee schema exists before yielding
        _run_schema_ddl(conn)
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
