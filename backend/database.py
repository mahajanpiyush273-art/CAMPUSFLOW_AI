"""
CampusFlow AI - Database Module
SQLite database setup, schema migration, FTS5 index, and helper methods.
All operations use parameterised queries and run in WAL mode with foreign keys enabled.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config import DATABASE_PATH, UPLOAD_DIR


def get_connection() -> sqlite3.Connection:
    """Open and configure a SQLite connection in WAL mode with row mapping."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initialize database tables, FTS5 virtual tables, and indexes."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Users table (students and admin staff)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin')),
                full_name TEXT NOT NULL,
                email TEXT NOT NULL
            );
        """)

        # 2. Student profiles table (source of form autofill data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_profiles (
                user_id INTEGER PRIMARY KEY,
                roll_no TEXT,
                enrollment_no TEXT,
                programme TEXT,
                department TEXT,
                semester TEXT,
                section TEXT,
                email TEXT,
                phone TEXT,
                hostel_block TEXT,
                room_no TEXT,
                guardian_name TEXT,
                guardian_phone TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Offices table (verified campus offices for student contact)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                hours TEXT NOT NULL,
                keywords TEXT NOT NULL
            );
        """)

        # 4. Forms table (official forms students can fill)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                office_id INTEGER,
                instructions TEXT,
                fields_json TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (office_id) REFERENCES offices(id) ON DELETE SET NULL
            );
        """)

        # 5. Documents table (notices, handbooks, rules, process guides, events, FAQs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                category TEXT NOT NULL,
                office_id INTEGER,
                department TEXT,
                publish_date TEXT NOT NULL,
                expiry_date TEXT,
                status TEXT NOT NULL CHECK(status IN ('draft', 'published', 'unpublished')),
                is_sample INTEGER DEFAULT 0,
                source_type TEXT NOT NULL,
                original_filename TEXT,
                stored_path TEXT,
                raw_text TEXT NOT NULL,
                summary TEXT,
                event_start TEXT,
                venue TEXT,
                registration_url TEXT,
                related_form_id INTEGER,
                ai_extraction TEXT,
                ai_flags TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                published_at TEXT,
                FOREIGN KEY (office_id) REFERENCES offices(id) ON DELETE SET NULL,
                FOREIGN KEY (related_form_id) REFERENCES forms(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            );
        """)

        # 6. Chunks table (document sections for retrieval)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                heading TEXT,
                text TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
        """)

        # 7. Chunks FTS5 virtual table for full-text search and BM25 ranking
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                title,
                heading,
                text,
                chunk_id UNINDEXED,
                document_id UNINDEXED
            );
        """)

        # 8. Deadlines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                due_date TEXT NOT NULL,
                due_time TEXT,
                status TEXT NOT NULL DEFAULT 'suggested',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
        """)

        # 9. Reminders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deadline_id INTEGER NOT NULL,
                remind_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                FOREIGN KEY (deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE
            );
        """)

        # 10. Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                link TEXT,
                deadline_id INTEGER,
                created_at TEXT NOT NULL,
                read_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE,
                UNIQUE (user_id, deadline_id, kind)
            );
        """)

        # 11. Deadline Done tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deadline_done (
                user_id INTEGER NOT NULL,
                deadline_id INTEGER NOT NULL,
                done_at TEXT NOT NULL,
                PRIMARY KEY (user_id, deadline_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (deadline_id) REFERENCES deadlines(id) ON DELETE CASCADE
            );
        """)

        # 12. Form Submissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS form_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                values_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'submitted',
                confirmed_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 13. Chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 14. Questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                rewritten_query TEXT,
                group_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'answered',
                confidence INTEGER NOT NULL DEFAULT 0,
                level TEXT NOT NULL DEFAULT 'Not verified',
                answer TEXT NOT NULL,
                document_id INTEGER,
                chunk_ids_json TEXT,
                mode TEXT NOT NULL DEFAULT 'ai',
                provider TEXT,
                topic TEXT,
                helpful INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
            );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status_date ON documents(status, publish_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deadlines_due_date ON deadlines(due_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_status_group ON questions(status, group_key);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read_at);")

        conn.commit()

    # Import legacy notices from backup if applicable
    _import_legacy_notices_if_any()


def _import_legacy_notices_if_any() -> None:
    """Import notices from old database backup if any rows exist."""
    old_db = DATABASE_PATH.parent / "campusflow.old.db"
    if not old_db.exists():
        return

    try:
        old_conn = sqlite3.connect(old_db)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()

        # Check if notices table exists in old db
        table_check = old_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notices';"
        ).fetchone()
        if not table_check:
            old_conn.close()
            return

        rows = old_cursor.execute("SELECT * FROM notices").fetchall()
        if not rows:
            old_conn.close()
            return

        with get_connection() as conn:
            cursor = conn.cursor()
            for r in rows:
                title = r["title"]
                category = r["category"] if "category" in r.keys() else "General"
                date_val = r["date"] if "date" in r.keys() else datetime.now().strftime("%Y-%m-%d")
                text_val = r["text"] if "text" in r.keys() else ""
                image_val = r["source_image"] if "source_image" in r.keys() else None

                # Check if already imported
                exists = cursor.execute("SELECT id FROM documents WHERE title = ?", (title,)).fetchone()
                if not exists and text_val:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        INSERT INTO documents (
                            title, doc_type, category, publish_date, status, is_sample,
                            source_type, original_filename, raw_text, summary, created_at, published_at
                        ) VALUES (?, 'notice', ?, ?, 'published', 0, 'file', ?, ?, ?, ?, ?)
                    """, (
                        title, category, date_val, image_val, text_val,
                        text_val[:200], now_str, now_str
                    ))
            conn.commit()
        old_conn.close()
    except Exception:
        pass


def reindex_document_fts(document_id: int) -> None:
    """Sync a document's chunks with the FTS5 virtual table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Delete existing FTS entries for this document
        cursor.execute("DELETE FROM chunks_fts WHERE document_id = ?", (str(document_id),))

        # Check if document is published
        doc = cursor.execute("SELECT id, title, status FROM documents WHERE id = ?", (document_id,)).fetchone()
        if doc and doc["status"] == "published":
            chunks = cursor.execute(
                "SELECT id, heading, text FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                (document_id,)
            ).fetchall()
            for ch in chunks:
                cursor.execute("""
                    INSERT INTO chunks_fts(title, heading, text, chunk_id, document_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    doc["title"],
                    ch["heading"] or "",
                    ch["text"],
                    str(ch["id"]),
                    str(document_id)
                ))
        conn.commit()


def remove_document_fts(document_id: int) -> None:
    """Remove a document from the FTS5 virtual search index."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks_fts WHERE document_id = ?", (str(document_id),))
        conn.commit()
