"""
Database layer — SQLite persistence for members and attendance.
"""
import sqlite3
import os
import threading
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

# ── Dynamic Config ──────────────────────────────────────────────

def get_db_path():
    """Always returns the current DB_PATH from environment."""
    return os.environ.get("DB_PATH", "data/members.db")

def get_samples_dir():
    """Always returns the current SAMPLES_DIR from environment."""
    return os.environ.get("SAMPLES_DIR", "data/face_samples")

# ⚠️ LEGACY CONSTANTS (Avoid using in new code — use getters instead)
# These are frozen at import time and may not reflect env changes in tests.
DB_PATH = get_db_path()
SAMPLES_DIR = get_samples_dir()

# ── Optimization Flag ──────────────────────────────────────────
_initialized_paths: set[str] = set()
_init_lock = threading.Lock()


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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username        TEXT PRIMARY KEY,
            hashed_password TEXT NOT NULL
        )
    """)
    conn.commit()


@contextmanager
def get_db():
    """
    Yield a database connection with auto-close.
    Ensures schema exists for the target DB_PATH exactly once per process.
    """
    path = get_db_path()
    uri = path.startswith("file:")
    
    # Check if we need to initialize this specific path
    if path not in _initialized_paths:
        with _init_lock:
            if path not in _initialized_paths:
                if not uri and os.path.dirname(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                
                # Temporary connection to initialize
                temp_conn = sqlite3.connect(path, uri=uri)
                try:
                    _run_schema_ddl(temp_conn)
                finally:
                    temp_conn.close()
                
                _initialized_paths.add(path)
                
    # Standard connection for the caller
    conn = sqlite3.connect(path, uri=uri)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Member CRUD ─────────────────────────────────────────────────

def create_member(name: str, expiration_date: str) -> dict:
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


# ── Admin CRUD ──────────────────────────────────────────────────

def get_admin(username: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def create_admin(username: str, hashed_password: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (username, hashed_password) VALUES (?, ?)",
            (username, hashed_password),
        )
        conn.commit()
