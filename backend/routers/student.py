"""
CampusFlow AI - Student Router
Handles Ask chat, questions history, notices & handbooks, events,
deadlines, notifications, and student dashboard queries.
"""

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.answer import answer_student_question, check_rate_limit
from backend.database import get_connection
from backend.ingest import is_document_expired
from backend.security import require_role

router = APIRouter(prefix="/api", tags=["Student"])


class AskRequest(BaseModel):
    question: str
    chat_id: Optional[int] = None


class ChatCreateRequest(BaseModel):
    title: Optional[str] = None


class FeedbackRequest(BaseModel):
    helpful: int  # 1 for up, -1 for down


@router.post("/ask")
async def ask_question(
    payload: AskRequest,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """
    Main Ask endpoint for students:
    Answers questions strictly from verified notices, enforces 20 req/min rate limit,
    and returns source citations and confidence score.
    """
    user_id = user["id"]
    if not check_rate_limit(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before asking another question."
        )

    q_text = payload.question.strip()
    if not q_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    chat_id = payload.chat_id
    recent_history: List[Dict[str, str]] = []

    with get_connection() as conn:
        cursor = conn.cursor()
        if not chat_id:
            # Create a new chat session titled with first few words
            chat_title = q_text[:35] + ("..." if len(q_text) > 35 else "")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO chats (user_id, title, created_at) VALUES (?, ?, ?)",
                (user_id, chat_title, now_str)
            )
            chat_id = cursor.lastrowid
            conn.commit()
        else:
            # Fetch recent turns for contextual follow-up
            turns = cursor.execute("""
                SELECT text, answer FROM questions
                WHERE chat_id = ? ORDER BY id DESC LIMIT 4
            """, (chat_id,)).fetchall()
            for t in reversed(turns):
                recent_history.append({"role": "student", "content": t["text"]})
                recent_history.append({"role": "assistant", "content": t["answer"]})

    # Execute ask pipeline
    result = answer_student_question(
        question=q_text,
        user_id=user_id,
        chat_id=chat_id,
        recent_history=recent_history,
    )
    result["chat_id"] = chat_id
    return result


@router.get("/chats")
async def list_student_chats(user: Dict[str, Any] = Depends(require_role("student"))):
    """List student's recent chat sessions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT c.*, (SELECT COUNT(*) FROM questions q WHERE q.chat_id = c.id) as question_count
            FROM chats c
            WHERE c.user_id = ?
            ORDER BY c.id DESC LIMIT 25
        """, (user["id"],)).fetchall()

    return {"chats": [dict(r) for r in rows]}


@router.post("/chats")
async def create_new_chat(
    payload: Optional[ChatCreateRequest] = None,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Create a new chat conversation."""
    title = (payload.title if payload and payload.title else "New Conversation").strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (user_id, title, created_at) VALUES (?, ?, ?)",
            (user["id"], title, now_str)
        )
        chat_id = cursor.lastrowid
        conn.commit()

    return {"ok": True, "chat_id": chat_id, "title": title}


@router.get("/chats/{chat_id}")
async def get_chat_history(
    chat_id: int,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Retrieve all turns of a chat session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        chat = cursor.execute(
            "SELECT * FROM chats WHERE id = ? AND user_id = ?",
            (chat_id, user["id"])
        ).fetchone()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat conversation not found.")

        questions = cursor.execute("""
            SELECT q.*, d.title as doc_title, d.department as doc_dept, d.publish_date as doc_date,
                   d.doc_type, d.expiry_date
            FROM questions q
            LEFT JOIN documents d ON d.id = q.document_id
            WHERE q.chat_id = ?
            ORDER BY q.id ASC
        """, (chat_id,)).fetchall()

    turns = []
    for q in questions:
        qd = dict(q)
        source = None
        if qd.get("document_id") and qd.get("doc_title"):
            source = {
                "id": qd["document_id"],
                "title": qd["doc_title"],
                "department": qd.get("doc_dept") or "Campus Office",
                "publish_date": qd["doc_date"],
                "doc_type": qd.get("doc_type"),
                "old": is_document_expired(qd.get("expiry_date")),
            }
        turns.append({
            "id": qd["id"],
            "question": qd["text"],
            "answer": qd["answer"],
            "status": qd["status"],
            "confidence": qd["confidence"],
            "level": qd["level"],
            "source": source,
            "created_at": qd["created_at"],
            "helpful": qd.get("helpful"),
        })

    return {"chat": dict(chat), "turns": turns}


@router.get("/questions")
async def get_my_questions(user: Dict[str, Any] = Depends(require_role("student"))):
    """List all questions asked by the student with status and admin answers."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT q.*, d.title as doc_title, d.publish_date as doc_date
            FROM questions q
            LEFT JOIN documents d ON d.id = q.document_id
            WHERE q.user_id = ?
            ORDER BY q.id DESC
        """, (user["id"],)).fetchall()

    return {"questions": [dict(r) for r in rows]}


@router.post("/questions/{question_id}/feedback")
async def record_question_feedback(
    question_id: int,
    payload: FeedbackRequest,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Record thumbs up (+1) or thumbs down (-1) on an answer."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE questions SET helpful = ? WHERE id = ? AND user_id = ?",
            (payload.helpful, question_id, user["id"])
        )
        conn.commit()

    return {"ok": True, "message": "Feedback recorded. Thank you!"}


@router.get("/documents")
async def list_student_documents(
    doc_type: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    include_old: bool = False,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """
    Information Hub: notices, handbooks, rules, process guides, newest first.
    Filters out drafts and unpublished documents.
    """
    sql = "SELECT * FROM documents WHERE status = 'published'"
    params = []

    if doc_type:
        sql += " AND doc_type = ?"
        params.append(doc_type)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND (title LIKE ? OR raw_text LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    sql += " ORDER BY publish_date DESC, id DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(sql, params).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["old"] = is_document_expired(d.get("expiry_date"))
        if not include_old and d["old"]:
            continue
        results.append(d)

    return {"documents": results, "count": len(results)}


@router.get("/documents/{document_id}")
async def get_student_document(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Retrieve full details of a published document."""
    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute(
            "SELECT * FROM documents WHERE id = ? AND status = 'published'",
            (document_id,)
        ).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        deadlines = cursor.execute(
            "SELECT * FROM deadlines WHERE document_id = ? AND status = 'confirmed'",
            (document_id,)
        ).fetchall()

    doc_dict = dict(doc)
    doc_dict["old"] = is_document_expired(doc_dict.get("expiry_date"))
    doc_dict["deadlines"] = [dict(d) for d in deadlines]
    return {"document": doc_dict}


@router.get("/documents/{document_id}/file")
async def download_document_file(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Download attached original notice file if present."""
    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute(
            "SELECT stored_path, original_filename FROM documents WHERE id = ? AND status = 'published'",
            (document_id,)
        ).fetchone()

    if not doc or not doc["stored_path"]:
        raise HTTPException(status_code=404, detail="No attached file for this notice.")

    p = Path(doc["stored_path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="File is missing from server storage.")

    return FileResponse(p, filename=doc["original_filename"] or p.name)


@router.get("/events")
async def list_events(user: Dict[str, Any] = Depends(require_role("student"))):
    """Retrieve published upcoming campus events with venue and countdown."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT * FROM documents
            WHERE doc_type = 'event' AND status = 'published'
            ORDER BY event_start ASC, publish_date DESC
        """).fetchall()

    events = []
    for r in rows:
        ed = dict(r)
        ed["old"] = is_document_expired(ed.get("expiry_date"))
        events.append(ed)

    return {"events": events}


@router.get("/deadlines")
async def list_deadlines(user: Dict[str, Any] = Depends(require_role("student"))):
    """
    List upcoming campus deadlines with 'done' status.
    Categorized into: Overdue, Today, Next 2 Days, This Month, Later.
    """
    user_id = user["id"]
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT d.*, doc.title as doc_title, doc.category, doc.department,
                   CASE WHEN dd.done_at IS NOT NULL THEN 1 ELSE 0 END as is_done
            FROM deadlines d
            JOIN documents doc ON doc.id = d.document_id
            LEFT JOIN deadline_done dd ON dd.deadline_id = d.id AND dd.user_id = ?
            WHERE d.status = 'confirmed' AND doc.status = 'published'
            ORDER BY d.due_date ASC
        """, (user_id,)).fetchall()

    deadlines = [dict(r) for r in rows]
    return {"deadlines": deadlines}


@router.post("/deadlines/{deadline_id}/done")
async def toggle_deadline_done(
    deadline_id: int,
    user: Dict[str, Any] = Depends(require_role("student")),
):
    """Toggle deadline done status for current student."""
    user_id = user["id"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        exists = cursor.execute(
            "SELECT * FROM deadline_done WHERE user_id = ? AND deadline_id = ?",
            (user_id, deadline_id)
        ).fetchone()

        if exists:
            cursor.execute("DELETE FROM deadline_done WHERE user_id = ? AND deadline_id = ?", (user_id, deadline_id))
            is_done = False
        else:
            cursor.execute(
                "INSERT INTO deadline_done (user_id, deadline_id, done_at) VALUES (?, ?, ?)",
                (user_id, deadline_id, now_str)
            )
            is_done = True
        conn.commit()

    return {"ok": True, "deadline_id": deadline_id, "is_done": is_done}


@router.get("/notifications")
async def get_student_notifications(user: Dict[str, Any] = Depends(require_role("student"))):
    """List unread notifications and alerts for student."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 20
        """, (user["id"],)).fetchall()

    notifs = [dict(r) for r in rows]
    unread_count = sum(1 for n in notifs if not n.get("read_at"))
    return {"notifications": notifs, "unread_count": unread_count}


@router.post("/notifications/read")
async def mark_notifications_read(user: Dict[str, Any] = Depends(require_role("student"))):
    """Mark all notifications as read for current student."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
            (now_str, user["id"])
        )
        conn.commit()

    return {"ok": True, "message": "All notifications marked as read."}


@router.get("/offices")
async def get_campus_offices():
    """List verified campus offices for student contact."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM offices ORDER BY name ASC").fetchall()
    return {"offices": [dict(r) for r in rows]}


@router.get("/student/dashboard")
async def get_student_dashboard(user: Dict[str, Any] = Depends(require_role("student"))):
    """
    Composite dashboard feed:
    - Due soon deadlines (within 7 days)
    - Latest published notices (newest first)
    - Upcoming events
    - Quick status of not-verified questions
    """
    user_id = user["id"]
    with get_connection() as conn:
        cursor = conn.cursor()

        # Due soon deadlines
        deadlines_rows = cursor.execute("""
            SELECT d.*, doc.title as doc_title,
                   CASE WHEN dd.done_at IS NOT NULL THEN 1 ELSE 0 END as is_done
            FROM deadlines d
            JOIN documents doc ON doc.id = d.document_id
            LEFT JOIN deadline_done dd ON dd.deadline_id = d.id AND dd.user_id = ?
            WHERE d.status = 'confirmed' AND doc.status = 'published'
            ORDER BY d.due_date ASC LIMIT 5
        """, (user_id,)).fetchall()

        # Latest notices
        notices_rows = cursor.execute("""
            SELECT * FROM documents
            WHERE status = 'published' AND doc_type != 'event'
            ORDER BY publish_date DESC, id DESC LIMIT 6
        """).fetchall()

        # Upcoming events
        events_rows = cursor.execute("""
            SELECT * FROM documents
            WHERE status = 'published' AND doc_type = 'event'
            ORDER BY event_start ASC LIMIT 3
        """).fetchall()

        # My pending review questions
        pending_q_count = cursor.execute("""
            SELECT COUNT(*) FROM questions
            WHERE user_id = ? AND status = 'not_verified'
        """, (user_id,)).fetchone()[0]

    notices = []
    for r in notices_rows:
        nd = dict(r)
        nd["old"] = is_document_expired(nd.get("expiry_date"))
        notices.append(nd)

    return {
        "greeting": f"Welcome back, {user['full_name']}!",
        "due_soon": [dict(r) for r in deadlines_rows],
        "latest_notices": notices,
        "upcoming_events": [dict(r) for r in events_rows],
        "pending_questions_count": pending_q_count,
    }
