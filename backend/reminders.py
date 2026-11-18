"""
CampusFlow AI - Background Reminders & Notification Service
Periodically scans confirmed deadlines, evaluates 2-day and 1-day reminder windows,
and dispatches notifications to students who have not marked the deadline done.
Also handles admin reply dispatch notifications.
"""

import asyncio
from datetime import datetime
from typing import Optional

from backend.database import get_connection


async def run_reminder_worker() -> None:
    """Async background worker running every 30 seconds to trigger due reminders."""
    while True:
        try:
            check_and_dispatch_reminders()
        except asyncio.CancelledError:
            break
        except Exception:
            pass
        try:
            await asyncio.sleep(30.0)
        except asyncio.CancelledError:
            break


def check_and_dispatch_reminders() -> int:
    """
    Scan reminders whose remind_at <= now, and create notifications for students
    who have not marked the deadline as done.
    Returns the number of notifications created.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_count = 0

    with get_connection() as conn:
        cursor = conn.cursor()

        # Find all reminders that have reached their scheduled time
        due_reminders = cursor.execute("""
            SELECT r.id AS reminder_id, r.deadline_id, r.kind, r.remind_at,
                   d.label, d.due_date, d.due_time, doc.title AS doc_title
            FROM reminders r
            JOIN deadlines d ON d.id = r.deadline_id
            JOIN documents doc ON doc.id = d.document_id
            WHERE r.remind_at <= ? AND d.status = 'confirmed' AND doc.status = 'published'
        """, (now_str,)).fetchall()

        if not due_reminders:
            return 0

        # Fetch all student user IDs
        students = cursor.execute("SELECT id FROM users WHERE role = 'student'").fetchall()
        student_ids = [s["id"] for s in students]

        for rem in due_reminders:
            deadline_id = rem["deadline_id"]
            kind = rem["kind"]
            label = rem["label"]
            due_date = rem["due_date"]
            doc_title = rem["doc_title"]

            day_desc = "in 2 days" if kind == "2d" else "tomorrow"
            notif_title = f"Due Soon: {label}"
            notif_body = f"'{label}' from notice '{doc_title}' is due {day_desc} ({due_date})."
            notif_link = "#/deadlines"

            for s_id in student_ids:
                # Check if student marked this deadline done
                is_done = cursor.execute(
                    "SELECT 1 FROM deadline_done WHERE user_id = ? AND deadline_id = ?",
                    (s_id, deadline_id)
                ).fetchone()

                if not is_done:
                    # Insert notification if not already sent (UNIQUE constraint prevents duplicate)
                    try:
                        cursor.execute("""
                            INSERT INTO notifications (
                                user_id, kind, title, body, link, deadline_id, created_at
                            ) VALUES (?, 'deadline', ?, ?, ?, ?, ?)
                        """, (s_id, notif_title, notif_body, notif_link, deadline_id, now_str))
                        created_count += 1
                    except Exception:
                        # Duplicate notification ignored
                        pass

        conn.commit()

    return created_count


def notify_student_reply(user_id: int, question_text: str, reply_text: str) -> None:
    """Create a notification when an admin answers a student's unverified question."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = "Admin Verified Your Question"
    snippet = reply_text[:90] + ("..." if len(reply_text) > 90 else "")
    body = f"An admin replied to '{question_text[:40]}...': {snippet}"
    link = "#/my-questions"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (
                user_id, kind, title, body, link, deadline_id, created_at
            ) VALUES (?, 'reply', ?, ?, ?, NULL, ?)
        """, (user_id, title, body, link, now_str))
        conn.commit()
