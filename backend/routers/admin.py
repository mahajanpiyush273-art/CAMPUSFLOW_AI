"""
CampusFlow AI - Admin Router
Handles document upload, AI extraction, review & recheck loop, publishing,
unpublishing, deletions, deadline scheduling, and system health checks.
"""

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from backend.config import CATEGORIES, DOC_TYPES, UPLOAD_DIR
from backend.database import get_connection
from backend.extraction import extract_and_validate_document, run_deterministic_validators
from backend.ingest import extract_text_from_file, index_document, remove_document_index
from backend.llm import get_provider_health
from backend.reminders import notify_student_reply
from backend.search import search_fts5_chunks
from backend.security import require_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class DeadlineItem(BaseModel):
    label: str
    date: str
    time: Optional[str] = None
    evidence: Optional[str] = None


class EventDetails(BaseModel):
    start: Optional[str] = None
    venue: Optional[str] = None
    registration_url: Optional[str] = None


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    office_id: Optional[int] = None
    publish_date: Optional[str] = None
    expiry_date: Optional[str] = None
    raw_text: Optional[str] = None
    summary: Optional[str] = None
    related_form_id: Optional[int] = None
    event_start: Optional[str] = None
    venue: Optional[str] = None
    registration_url: Optional[str] = None
    deadlines: Optional[List[DeadlineItem]] = None


class PublishRequest(BaseModel):
    confirmed: bool


@router.get("/health")
async def admin_health_check(user: Dict[str, Any] = Depends(require_role("admin"))):
    """Return AI model provider availability and active configurations without exposing keys."""
    return get_provider_health()


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    pasted_text: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Step 1 & 2 of Admin Wizard:
    Accepts file upload (PDF/Word/Text/Image) OR pasted text.
    Creates a hidden DRAFT document, runs AI extraction + deterministic validation,
    and returns the draft metadata and flags.
    """
    raw_text = ""
    source_type = "typed"
    original_filename = None
    stored_path = None

    if file and file.filename:
        original_filename = file.filename
        source_type = "file" if not Path(file.filename).suffix.lower() in [".png", ".jpg", ".jpeg"] else "image"
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Save to uploads directory with timestamped unique filename
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = f"{int(time.time())}_{Path(file.filename).name.replace(' ', '_')}"
        dest_path = UPLOAD_DIR / safe_name
        dest_path.write_bytes(file_bytes)
        stored_path = str(dest_path)

        # Extract readable text
        raw_text = extract_text_from_file(file_bytes, filename=file.filename, mime_type=file.content_type)

    elif pasted_text and pasted_text.strip():
        raw_text = pasted_text.strip()
        source_type = "typed"

    else:
        raise HTTPException(
            status_code=400,
            detail="Please upload a document file (PDF, Word, Image, Text) or paste the notice text."
        )

    # Run AI extraction and deterministic validation
    extraction_result = extract_and_validate_document(raw_text, default_doc_type=doc_type)
    fields = extraction_result["fields"]
    flags = extraction_result["flags"]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert draft document into database (hidden from students)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (
                title, doc_type, category, department, publish_date, expiry_date,
                status, is_sample, source_type, original_filename, stored_path,
                raw_text, summary, event_start, venue, registration_url,
                ai_extraction, ai_flags, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'draft', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fields.get("title") or "Untitled Notice",
            fields.get("doc_type") or (doc_type or "notice"),
            fields.get("category") or "General",
            fields.get("department"),
            fields.get("publish_date") or date.today().isoformat(),
            fields.get("expiry_date"),
            source_type,
            original_filename,
            stored_path,
            raw_text,
            fields.get("summary"),
            fields.get("event", {}).get("start"),
            fields.get("event", {}).get("venue"),
            fields.get("event", {}).get("registration_url"),
            json.dumps(fields),
            json.dumps(flags),
            user["id"],
            now_str,
        ))
        draft_id = cursor.lastrowid
        conn.commit()

    return {
        "ok": True,
        "id": draft_id,
        "document_id": draft_id,
        "draft_id": draft_id,
        "status": "draft",
        "title": fields.get("title") or "Untitled Notice",
        "doc_type": fields.get("doc_type") or (doc_type or "Notice"),
        "category": fields.get("category") or "Other",
        "department": fields.get("department") or "",
        "office_id": fields.get("office_id"),
        "publish_date": fields.get("publish_date") or date.today().isoformat(),
        "expiry_date": fields.get("expiry_date"),
        "raw_text": raw_text,
        "summary": fields.get("summary") or "",
        "event_start": fields.get("event", {}).get("start"),
        "venue": fields.get("event", {}).get("venue"),
        "registration_url": fields.get("event", {}).get("registration_url"),
        "deadlines": fields.get("deadlines") or [],
        "flags": flags,
        "provider": extraction_result.get("provider"),
        "model": extraction_result.get("model"),
    }


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None,
    category: Optional[str] = None,
    doc_type: Optional[str] = None,
    q: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Retrieve list of documents for administration."""
    query = "SELECT * FROM documents WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if doc_type:
        query += " AND doc_type = ?"
        params.append(doc_type)
    if q:
        query += " AND (title LIKE ? OR raw_text LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    query += " ORDER BY id DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(query, params).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["ai_flags"] = json.loads(d["ai_flags"]) if d.get("ai_flags") else []
        d["ai_extraction"] = json.loads(d["ai_extraction"]) if d.get("ai_extraction") else {}
        results.append(d)

    return {"documents": results, "count": len(results)}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Retrieve single document details with its deadlines and flags."""
    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        deadlines = cursor.execute(
            "SELECT * FROM deadlines WHERE document_id = ?",
            (document_id,)
        ).fetchall()

    doc_dict = dict(doc)
    doc_dict["ai_flags"] = json.loads(doc_dict["ai_flags"]) if doc_dict.get("ai_flags") else []
    doc_dict["ai_extraction"] = json.loads(doc_dict["ai_extraction"]) if doc_dict.get("ai_extraction") else {}
    doc_dict["deadlines"] = [dict(dl) for dl in deadlines]

    return {"document": doc_dict}


@router.put("/documents/{document_id}")
async def update_document(
    document_id: int,
    payload: DocumentUpdateRequest,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Update document fields during review or for published documents."""
    data = payload.model_dump(exclude_unset=True)
    deadlines = data.pop("deadlines", None)

    with get_connection() as conn:
        cursor = conn.cursor()
        exists = cursor.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Document not found.")

        if data:
            set_clauses = [f"{col} = ?" for col in data.keys()]
            cursor.execute(
                f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = ?",
                list(data.values()) + [document_id]
            )

        # Update deadlines if provided
        if deadlines is not None:
            cursor.execute("DELETE FROM deadlines WHERE document_id = ?", (document_id,))
            for dl in deadlines:
                cursor.execute("""
                    INSERT INTO deadlines (document_id, label, due_date, due_time, status)
                    VALUES (?, ?, ?, ?, 'suggested')
                """, (document_id, dl["label"], dl["date"], dl.get("time")))

        conn.commit()

        # Fetch updated doc and deadlines
        updated_doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        updated_deadlines = cursor.execute("SELECT * FROM deadlines WHERE document_id = ?", (document_id,)).fetchall()

    doc_dict = dict(updated_doc)
    doc_dict["flags"] = json.loads(doc_dict["ai_flags"]) if doc_dict.get("ai_flags") else []
    doc_dict["deadlines"] = [{"label": dl["label"], "date": dl["due_date"], "time": dl["due_time"]} for dl in updated_deadlines]

    return {"ok": True, "message": "Document updated successfully.", "document": doc_dict}


@router.post("/documents/{document_id}/recheck")
async def recheck_document(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Recheck Loop: Re-runs deterministic validation checks over updated document text & metadata.
    Updates the stored ai_flags.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        deadlines = cursor.execute(
            "SELECT label, due_date, due_time FROM deadlines WHERE document_id = ?",
            (document_id,)
        ).fetchall()

    fields = {
        "title": doc["title"],
        "category": doc["category"],
        "department": doc["department"],
        "doc_type": doc["doc_type"],
        "publish_date": doc["publish_date"],
        "expiry_date": doc["expiry_date"],
        "deadlines": [{"label": dl["label"], "date": dl["due_date"], "time": dl["due_time"]} for dl in deadlines],
        "event": {"start": doc["event_start"], "venue": doc["venue"]},
    }

    flags = run_deterministic_validators(fields, doc["raw_text"])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE documents SET ai_flags = ? WHERE id = ?",
            (json.dumps(flags), document_id)
        )
        conn.commit()

    return {"ok": True, "flags": flags, "blocking_count": sum(1 for f in flags if f.get("severity") == "blocking")}


@router.post("/documents/{document_id}/publish")
async def publish_document(
    document_id: int,
    payload: PublishRequest,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Publish Document:
    Enforces that the admin confirmed all details and that NO blocking flags exist.
    Indexes chunks in FTS5 and schedules reminders for all confirmed deadlines.
    """
    if not payload.confirmed:
        raise HTTPException(
            status_code=400,
            detail="You must confirm the dates, category, and department before publishing."
        )

    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        flags = json.loads(doc["ai_flags"]) if doc["ai_flags"] else []
        blocking_flags = [f for f in flags if f.get("severity") == "blocking"]
        if blocking_flags:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot publish document with blocking validation flags: {blocking_flags[0]['message']}"
            )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update document status to published
        cursor.execute(
            "UPDATE documents SET status = 'published', published_at = ? WHERE id = ?",
            (now_str, document_id)
        )

        # Mark deadlines as confirmed and schedule reminders
        deadlines = cursor.execute(
            "SELECT id, due_date FROM deadlines WHERE document_id = ?",
            (document_id,)
        ).fetchall()

        cursor.execute("UPDATE deadlines SET status = 'confirmed' WHERE document_id = ?", (document_id,))

        for dl in deadlines:
            dl_id = dl["id"]
            due_str = dl["due_date"]
            try:
                due_dt = datetime.strptime(due_str, "%Y-%m-%d")
                # 2 days prior and 1 day prior at 09:00
                remind_2d = (due_dt - timedelta(days=2)).strftime("%Y-%m-%d 09:00:00")
                remind_1d = (due_dt - timedelta(days=1)).strftime("%Y-%m-%d 09:00:00")

                # If due within 2 days, set reminder time to past so notification fires immediately
                if due_dt.date() - date.today() <= timedelta(days=2):
                    remind_2d = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO reminders (deadline_id, remind_at, kind)
                    VALUES (?, ?, '2d'), (?, ?, '1d')
                """, (dl_id, remind_2d, dl_id, remind_1d))
            except Exception:
                continue

        conn.commit()

    # Index chunks in FTS5 for search
    indexed_chunks = index_document(document_id)

    return {
        "ok": True,
        "status": "published",
        "message": f"Published '{doc['title']}' successfully to student feed.",
        "chunk_count": indexed_chunks,
        "indexed_chunks": indexed_chunks,
        "scheduled_reminders": len(deadlines) * 2,
        "deadlines_confirmed": len(deadlines),
    }


@router.post("/documents/{document_id}/unpublish")
async def unpublish_document(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Unpublish a document: removes it from student feed and FTS5 search index."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET status = 'unpublished' WHERE id = ?", (document_id,))
        conn.commit()

    remove_document_index(document_id)
    return {"ok": True, "message": "Document unpublished and removed from student search index."}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Delete a document and clean up chunks, FTS index, and deadlines."""
    remove_document_index(document_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

    return {"ok": True, "message": "Document deleted successfully."}


class ReviewReplyRequest(BaseModel):
    group_key: str
    answer: str
    category: Optional[str] = "General"
    office_id: Optional[int] = None
    related_form_id: Optional[int] = None


@router.get("/review-queue")
async def get_review_queue(user: Dict[str, Any] = Depends(require_role("admin"))):
    """
    Review Queue:
    Groups unanswered student questions by group_key.
    Returns grouped list with repetition count and matching notice suggestions.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        groups = cursor.execute("""
            SELECT group_key, COUNT(*) as count, MAX(created_at) as last_asked,
                   MIN(text) as sample_question, COUNT(DISTINCT user_id) as students_count
            FROM questions
            WHERE status = 'not_verified'
            GROUP BY group_key
            ORDER BY count DESC, last_asked DESC
        """).fetchall()

    results = []
    for g in groups:
        sample_q = g["sample_question"]
        suggested = search_fts5_chunks(sample_q, limit=2)
        results.append({
            "group_key": g["group_key"],
            "count": g["count"],
            "sample_question": sample_q,
            "last_asked": g["last_asked"],
            "students_count": g["students_count"],
            "suggested_notices": [
                {"id": s["document_id"], "title": s["doc_title"], "department": s.get("department")}
                for s in suggested
            ],
        })

    return {"queue": results, "total_pending": sum(g["count"] for g in results)}


@router.post("/review-queue/reply")
async def reply_review_queue(
    payload: ReviewReplyRequest,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Publish Verified Answer Once for all students:
    1. Creates a published FAQ document in documents table and indexes in FTS5.
    2. Marks all questions with that group_key as admin_replied.
    3. Dispatches individual notifications to all students who asked.
    """
    answer_text = payload.answer.strip()
    if not answer_text:
        raise HTTPException(status_code=400, detail="Answer text cannot be empty.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        # Find all questions in this group
        pending_questions = cursor.execute("""
            SELECT id, user_id, text FROM questions
            WHERE group_key = ? AND status = 'not_verified'
        """, (payload.group_key,)).fetchall()

        if not pending_questions:
            raise HTTPException(status_code=404, detail="No unverified questions found for this group key.")

        sample_q = pending_questions[0]["text"]
        faq_title = f"FAQ: {sample_q[:65]}"
        raw_faq_text = f"Official FAQ: {sample_q}\n\nVerified Answer: {answer_text}"

        # 1. Create published FAQ document
        cursor.execute("""
            INSERT INTO documents (
                title, doc_type, category, office_id, publish_date, status,
                is_sample, source_type, raw_text, summary, related_form_id,
                created_by, created_at, published_at
            ) VALUES (?, 'faq', ?, ?, ?, 'published', 0, 'admin_answer', ?, ?, ?, ?, ?, ?)
        """, (
            faq_title, payload.category or "General", payload.office_id,
            date.today().isoformat(), raw_faq_text, answer_text[:200],
            payload.related_form_id, user["id"], now_str, now_str
        ))
        faq_doc_id = cursor.lastrowid

        # 2. Update questions status
        cursor.execute("""
            UPDATE questions
            SET status = 'admin_replied', answer = ?, document_id = ?
            WHERE group_key = ? AND status = 'not_verified'
        """, (answer_text, faq_doc_id, payload.group_key))

        conn.commit()

    # Index FAQ document in FTS5
    index_document(faq_doc_id)

    # 3. Notify each student
    for q in pending_questions:
        notify_student_reply(
            user_id=q["user_id"],
            question_text=q["text"],
            reply_text=answer_text,
        )

    return {
        "ok": True,
        "message": f"Verified answer published. Notified {len(pending_questions)} students.",
        "students_notified": len(pending_questions),
        "faq_document_id": faq_doc_id,
    }


@router.get("/stats")
async def get_admin_insights(user: Dict[str, Any] = Depends(require_role("admin"))):
    """
    Insights Dashboard metrics:
    - Questions answered vs not verified
    - Common/repeated questions
    - Topic breakdown
    - Deadlines met percentage
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Questions counts
        total_q = cursor.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        answered_q = cursor.execute("SELECT COUNT(*) FROM questions WHERE status = 'answered'").fetchone()[0]
        not_verified_q = cursor.execute("SELECT COUNT(*) FROM questions WHERE status = 'not_verified'").fetchone()[0]
        replied_q = cursor.execute("SELECT COUNT(*) FROM questions WHERE status = 'admin_replied'").fetchone()[0]

        # Average confidence
        avg_conf_row = cursor.execute("SELECT AVG(confidence) FROM questions WHERE status IN ('answered', 'admin_replied')").fetchone()[0]
        avg_confidence = int(round(avg_conf_row or 0))

        # Deadlines metrics
        total_deadlines = cursor.execute("SELECT COUNT(*) FROM deadlines WHERE status = 'confirmed'").fetchone()[0]
        total_done = cursor.execute("SELECT COUNT(*) FROM deadline_done").fetchone()[0]

        # Category breakdown
        category_rows = cursor.execute("""
            SELECT topic, COUNT(*) as count FROM questions
            WHERE topic IS NOT NULL GROUP BY topic ORDER BY count DESC LIMIT 6
        """).fetchall()

        # Top 5 most repeated questions
        top_repeated = cursor.execute("""
            SELECT group_key, MIN(text) as sample_question, COUNT(*) as count, status
            FROM questions
            GROUP BY group_key
            ORDER BY count DESC LIMIT 5
        """).fetchall()

        # Questions per day (last 7 days)
        daily_rows = cursor.execute("""
            SELECT SUBSTR(created_at, 1, 10) as day, COUNT(*) as count
            FROM questions
            GROUP BY day
            ORDER BY day DESC LIMIT 7
        """).fetchall()

        # Helpful rating
        up_count = cursor.execute("SELECT COUNT(*) FROM questions WHERE helpful = 1").fetchone()[0]
        down_count = cursor.execute("SELECT COUNT(*) FROM questions WHERE helpful = -1").fetchone()[0]
        total_feedback = up_count + down_count
        helpful_pct = int(round((up_count / total_feedback) * 100)) if total_feedback > 0 else 100

    answered_pct = int(round((answered_q / total_q) * 100)) if total_q > 0 else 0
    not_verified_pct = int(round((not_verified_q / total_q) * 100)) if total_q > 0 else 0

    return {
        "total_questions": total_q,
        "answered_count": answered_q,
        "answered_pct": answered_pct,
        "not_verified_count": not_verified_q,
        "not_verified_pct": not_verified_pct,
        "replied_count": replied_q,
        "pending_review_count": not_verified_q,
        "avg_confidence": avg_confidence,
        "active_deadlines": total_deadlines,
        "deadlines_marked_done": total_done,
        "helpful_pct": helpful_pct,
        "categories": [{"topic": r["topic"], "count": r["count"]} for r in category_rows],
        "top_repeated": [dict(r) for r in top_repeated],
        "daily_questions": list(reversed([dict(r) for r in daily_rows])),
    }


class SubmissionStatusUpdate(BaseModel):
    status: str


class OfficeCreateUpdate(BaseModel):
    name: str
    location: str
    phone: str
    email: str
    hours: str
    keywords: str


@router.get("/submissions")
async def list_admin_form_submissions(user: Dict[str, Any] = Depends(require_role("admin"))):
    """Read-only table of all student form submissions with values and review actions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT s.*, f.title as form_title, f.slug as form_slug,
                   u.full_name as student_name, u.email as student_email
            FROM form_submissions s
            JOIN forms f ON f.id = s.form_id
            JOIN users u ON u.id = s.user_id
            ORDER BY s.id DESC
        """).fetchall()

    submissions = []
    for r in rows:
        sd = dict(r)
        sd["ref_number"] = f"CF-{sd['id']:05d}"
        sd["values"] = json.loads(sd["values_json"])
        del sd["values_json"]
        submissions.append(sd)

    return {"submissions": submissions, "count": len(submissions)}


@router.patch("/submissions/{submission_id}")
async def update_form_submission_status(
    submission_id: int,
    payload: SubmissionStatusUpdate,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Mark a student form submission as 'reviewed' or 'submitted'."""
    with get_connection() as conn:
        cursor = conn.cursor()
        exists = cursor.execute("SELECT id FROM form_submissions WHERE id = ?", (submission_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Submission not found.")

        cursor.execute(
            "UPDATE form_submissions SET status = ? WHERE id = ?",
            (payload.status, submission_id)
        )
        conn.commit()

    return {"ok": True, "message": f"Submission status updated to '{payload.status}'."}


@router.get("/offices")
async def list_admin_offices(user: Dict[str, Any] = Depends(require_role("admin"))):
    """List all campus offices with contact details and matching keyword tags."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM offices ORDER BY id ASC").fetchall()
    return {"offices": [dict(r) for r in rows]}


@router.post("/offices")
async def create_office(
    payload: OfficeCreateUpdate,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Create a new campus office contact."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offices (name, location, phone, email, hours, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (payload.name, payload.location, payload.phone, payload.email, payload.hours, payload.keywords))
        new_id = cursor.lastrowid
        conn.commit()

    return {"ok": True, "office_id": new_id, "message": f"Office '{payload.name}' created."}


@router.put("/offices/{office_id}")
async def update_office(
    office_id: int,
    payload: OfficeCreateUpdate,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Update campus office location, contact hours, or keyword tags."""
    with get_connection() as conn:
        cursor = conn.cursor()
        exists = cursor.execute("SELECT id FROM offices WHERE id = ?", (office_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Office not found.")

        cursor.execute("""
            UPDATE offices
            SET name = ?, location = ?, phone = ?, email = ?, hours = ?, keywords = ?
            WHERE id = ?
        """, (payload.name, payload.location, payload.phone, payload.email, payload.hours, payload.keywords, office_id))
        conn.commit()

    return {"ok": True, "message": f"Office '{payload.name}' updated successfully."}
