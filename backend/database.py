import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path to the SQLite database in the project root
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "campusflow.db"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection with dict-like row access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the notices table if it does not already exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                notice_date TEXT NOT NULL,
                text TEXT NOT NULL,
                source_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def add_notice(
    title: str,
    category: str,
    notice_date: str,
    text: str,
    source_image: Optional[str] = None,
) -> int:
    """Insert a new notice into the database and return its row ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notices (title, category, notice_date, text, source_image)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title.strip(), category.strip(), notice_date.strip(), text.strip(), source_image),
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_all_notices(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve all notices ordered by newest first."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, category, notice_date, text, source_image, created_at
            FROM notices
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_notice_by_id(notice_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single notice by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, category, notice_date, text, source_image, created_at
            FROM notices
            WHERE id = ?
            """,
            (notice_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
