"""
CampusFlow AI - Ask Pipeline Engine
Orchestrates: query understanding, conversation context, FTS5 retrieval,
grounded LLM synthesis, confidence scoring, next-step actions, and
not-verified fallback with admin review queue integration.
"""

from datetime import datetime
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, VERIFIED_MIN_CONFIDENCE
from backend.database import get_connection
from backend.ingest import is_document_expired
from backend.llm import chat_json, chat_text
from backend.prompts import PROMPT_ANSWER_SYSTEM, PROMPT_UNDERSTAND_SYSTEM
from backend.search import (
    STOP_WORDS,
    clean_and_tokenize,
    compute_confidence_score,
    expand_query_with_synonyms,
    search_fts5_chunks,
)

# In-memory rate limiting: user_id -> list of timestamps
_user_request_timestamps: Dict[int, List[float]] = {}
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW = 60.0  # seconds


def check_rate_limit(user_id: int) -> bool:
    """Return True if request is allowed, False if user exceeded 20 req/min."""
    now = time.time()
    timestamps = _user_request_timestamps.get(user_id, [])
    # Keep only timestamps within the last 60 seconds
    valid_ts = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(valid_ts) >= RATE_LIMIT_REQUESTS:
        _user_request_timestamps[user_id] = valid_ts
        return False
    valid_ts.append(now)
    _user_request_timestamps[user_id] = valid_ts
    return True


def compute_group_key(question: str) -> str:
    """
    Generate normalized group key from sorted, lower-cased keywords
    so repeated questions group together in the admin review queue.
    """
    tokens = clean_and_tokenize(question)
    tokens = [t for t in tokens if t not in ["hai", "kya", "kab", "kaha", "kahan", "kaise", "kitna", "batao"]]
    if not tokens:
        tokens = [question.strip().lower()[:20]]
    return " ".join(sorted(set(tokens)))


def understand_query(
    question: str,
    recent_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Understand student question in context of previous turns.
    Identifies greetings, campus relevance, rewritten standalone question, and keywords.
    """
    q_clean = question.strip()
    q_lower = q_clean.lower()

    # Fast heuristic check for standard greetings
    greetings = {"hi", "hello", "hey", "good morning", "good evening", "namaste"}
    if q_lower in greetings or q_lower in {"thanks", "thank you", "dhanyawad"}:
        return {
            "is_campus_question": False,
            "is_greeting": True,
            "greeting_reply": "Hello! I am CampusFlow AI. Ask me any question about campus notices, fee deadlines, exam timetables, or events.",
            "rewritten_query": q_clean,
            "search_keywords": [],
            "language_style": "english",
        }

    # Safety: detect prompt injection / jailbreak patterns
    jailbreak_patterns = ["ignore previous", "ignore all", "system prompt", "tell me a joke", "write a poem", "who created you"]
    if any(p in q_lower for p in jailbreak_patterns):
        return {
            "is_campus_question": False,
            "is_greeting": False,
            "greeting_reply": None,
            "rewritten_query": q_clean,
            "search_keywords": [],
            "language_style": "english",
        }

    # Format recent history for query rewriting
    history_str = ""
    if recent_history:
        history_lines = []
        for turn in recent_history[-4:]:
            role = turn.get("role", "student")
            content = turn.get("content", "")
            history_lines.append(f"{role.capitalize()}: {content}")
        history_str = "\n".join(history_lines)

    user_prompt = f"Chat History:\n{history_str or 'None'}\n\nStudent Question:\n{q_clean}"

    llm_res, provider, model = chat_json(
        system_prompt=PROMPT_UNDERSTAND_SYSTEM,
        user_prompt=user_prompt,
        timeout=15.0,
    )

    if llm_res and isinstance(llm_res, dict):
        return llm_res

    # Offline / rule-based fallback
    rewritten = q_clean
    if recent_history:
        prev_text = " ".join([turn.get("content", "") for turn in recent_history[-2:]])
        context_words = [w for w in clean_and_tokenize(prev_text) if w in ["fee", "fees", "hostel", "exam", "exams", "room", "bonafide", "attendance"]]
        if context_words and not any(w in q_clean.lower() for w in context_words):
            rewritten = f"{context_words[0]} {q_clean}"

    tokens = clean_and_tokenize(rewritten)
    return {
        "is_campus_question": True,
        "is_greeting": False,
        "greeting_reply": None,
        "rewritten_query": rewritten,
        "search_keywords": tokens,
        "language_style": "hinglish" if any(w in q_lower for w in ["kab", "kahan", "kaha", "kitna", "kaise", "jama"]) else "english",
    }


def find_matched_sentence(text: str, question: str) -> str:
    """Find the sentence in notice text with highest keyword overlap to highlight as source evidence."""
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    kws = clean_and_tokenize(question)
    best_sent = ""
    best_score = 0

    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) < 15:
            continue
        s_lower = s_clean.lower()
        score = sum(1 for kw in kws if kw in s_lower)
        if score > best_score:
            best_score = score
            best_sent = s_clean

    return best_sent or (sentences[0] if sentences else text[:120])


def build_next_steps(
    document: Dict[str, Any],
    deadlines: List[Dict[str, Any]],
    office: Optional[Dict[str, Any]],
    form: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Construct actionable next steps from verified database relations."""
    next_steps = []

    # 1. Related official form action
    if form:
        next_steps.append({
            "type": "form",
            "label": f"Open Form: {form['title']}",
            "slug": form["slug"],
            "url": f"#/forms/{form['slug']}",
        })

    # 2. Event registration action
    if document.get("doc_type") == "event" and document.get("registration_url"):
        next_steps.append({
            "type": "event_register",
            "label": "Register for Event",
            "url": document["registration_url"],
            "external": True,
        })

    # 3. Deadline action
    if deadlines:
        next_steps.append({
            "type": "deadline",
            "label": f"Due {deadlines[0]['due_date']}: Mark Done",
            "deadline_id": deadlines[0]["id"],
        })

    # 4. Office contact action
    if office:
        next_steps.append({
            "type": "office_contact",
            "label": f"Contact {office['name']}",
            "phone": office["phone"],
            "email": office["email"],
            "location": office["location"],
        })

    # 5. Full notice viewer action
    next_steps.append({
        "type": "view_notice",
        "label": "View Full Notice",
        "document_id": document["document_id"],
    })

    return next_steps


def answer_student_question(
    question: str,
    user_id: int,
    chat_id: Optional[int] = None,
    recent_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Main Ask pipeline:
    1. Understand question & context
    2. Retrieve top FTS5 chunks
    3. Calculate grounded confidence
    4. Synthesize verified answer or construct Not-Verified fallback with office contacts
    5. Save question to database
    """
    q_clean = question.strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Understand question
    understanding = understand_query(q_clean, recent_history=recent_history)

    # Greeting handling
    if understanding.get("is_greeting") and understanding.get("greeting_reply"):
        return {
            "status": "greeting",
            "answer": understanding["greeting_reply"],
            "confidence": 100,
            "level": "High",
            "is_verified": True,
            "source": None,
            "next_steps": [],
            "office": None,
        }

    # Step 2: Retrieve matching chunks
    search_q = understanding.get("rewritten_query") or q_clean
    top_chunks = search_fts5_chunks(search_q, limit=6)

    # Step 3: If no chunks match at all -> Not Verified
    if not top_chunks or not understanding.get("is_campus_question", True):
        return _handle_not_verified(
            question=q_clean,
            user_id=user_id,
            chat_id=chat_id,
            confidence=0,
            search_query=search_q,
            now_str=now_str,
        )

    best_chunk = top_chunks[0]

    # Retrieve associated office and related form
    with get_connection() as conn:
        cursor = conn.cursor()
        office = None
        if best_chunk.get("office_id"):
            o_row = cursor.execute("SELECT * FROM offices WHERE id = ?", (best_chunk["office_id"],)).fetchone()
            if o_row:
                office = dict(o_row)

        form = None
        if best_chunk.get("related_form_id"):
            f_row = cursor.execute("SELECT * FROM forms WHERE id = ?", (best_chunk["related_form_id"],)).fetchone()
            if f_row:
                form = dict(f_row)

        deadlines = cursor.execute(
            "SELECT * FROM deadlines WHERE document_id = ? ORDER BY due_date ASC",
            (best_chunk["document_id"],)
        ).fetchall()
        deadlines_list = [dict(d) for d in deadlines]

    # Step 4: Synthesize answer with LLM using strictly the retrieved excerpts
    excerpts_text = "\n\n---\n\n".join([
        f"Notice Title: {c['doc_title']}\n"
        f"Heading: {c['heading']}\n"
        f"Excerpt: {c['chunk_text']}\n"
        f"Published: {c['publish_date']}" + (" (WARNING: Notice is EXPIRED / OLD)" if c.get("old") else "")
        for c in top_chunks[:3]
    ])

    user_prompt = (
        f"STUDENT QUESTION:\n{q_clean}\n\n"
        f"OFFICIAL CAMPUS NOTICE EXCERPTS:\n{excerpts_text}"
    )

    llm_answer_json, provider, model = chat_json(
        system_prompt=PROMPT_ANSWER_SYSTEM,
        user_prompt=user_prompt,
        timeout=20.0,
    )

    is_offline = (provider == "offline")
    llm_can_answer = bool(llm_answer_json and llm_answer_json.get("can_answer", False))

    # Compute grounded confidence score
    confidence, level = compute_confidence_score(
        question=q_clean,
        top_chunk=best_chunk,
        llm_answered_ok=llm_can_answer,
        is_offline=is_offline,
    )

    # If confidence is below threshold or LLM explicitly could not answer -> Not Verified
    if confidence < VERIFIED_MIN_CONFIDENCE or (not llm_can_answer and not is_offline):
        return _handle_not_verified(
            question=q_clean,
            user_id=user_id,
            chat_id=chat_id,
            confidence=confidence,
            search_query=search_q,
            now_str=now_str,
            suggested_office=office,
        )

    # Prepare verified answer text
    if llm_can_answer and llm_answer_json:
        final_answer = llm_answer_json.get("answer", "")
    else:
        # Offline mode: extract the best matching sentence from notice
        best_sentence = find_matched_sentence(best_chunk["chunk_text"], q_clean)
        final_answer = f"AI is offline: showing the exact line from the notice: \"{best_sentence}\""

    matched_sentence = find_matched_sentence(best_chunk["chunk_text"], q_clean)
    next_steps = build_next_steps(best_chunk, deadlines_list, office, form)

    # Save answered question to database
    group_key = compute_group_key(q_clean)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO questions (
                chat_id, user_id, text, rewritten_query, group_key, status,
                confidence, level, answer, document_id, chunk_ids_json, mode,
                provider, topic, created_at
            ) VALUES (?, ?, ?, ?, ?, 'answered', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id, user_id, q_clean, search_q, group_key,
            confidence, level, final_answer, best_chunk["document_id"],
            json.dumps([best_chunk["chunk_id"]]),
            "offline" if is_offline else "ai",
            provider, best_chunk.get("category"), now_str
        ))
        question_id = cursor.lastrowid
        conn.commit()

    return {
        "question_id": question_id,
        "status": "answered",
        "answer": final_answer,
        "confidence": confidence,
        "level": level,
        "is_verified": True,
        "mode": "offline" if is_offline else "ai",
        "provider": provider,
        "source": {
            "id": best_chunk["document_id"],
            "title": best_chunk["doc_title"],
            "publish_date": best_chunk["publish_date"],
            "department": best_chunk["department"] or best_chunk.get("category", "Campus Office"),
            "doc_type": best_chunk["doc_type"],
            "old": best_chunk.get("old", False),
            "highlight": matched_sentence,
            "full_text": best_chunk.get("full_doc_text", best_chunk["chunk_text"]),
        },
        "next_steps": next_steps,
        "office": office,
    }


def _handle_not_verified(
    question: str,
    user_id: int,
    chat_id: Optional[int],
    confidence: int,
    search_query: str,
    now_str: str,
    suggested_office: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct fallback response when confidence is below threshold.
    Enforces the core hackathon promise: NEVER GUESS.
    Saves question with status='not_verified' to the admin review queue.
    """
    # Find best office contact based on keyword mapping or default
    office_to_show = suggested_office
    if not office_to_show:
        with get_connection() as conn:
            cursor = conn.cursor()
            offices = cursor.execute("SELECT * FROM offices").fetchall()
            q_lower = question.lower()
            for o in offices:
                kws = [k.strip().lower() for k in o["keywords"].split(",") if k.strip()]
                if any(k in q_lower for k in kws):
                    office_to_show = dict(o)
                    break
            if not office_to_show and offices:
                office_to_show = dict(offices[0])

    fallback_msg = (
        "No confirmed answer exists in official notices. "
        "Your question has been forwarded to the campus admin review list. "
        "You can check for the verified reply in 'My Questions', or contact the office below directly."
    )

    group_key = compute_group_key(question)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO questions (
                chat_id, user_id, text, rewritten_query, group_key, status,
                confidence, level, answer, document_id, chunk_ids_json, mode,
                provider, topic, created_at
            ) VALUES (?, ?, ?, ?, ?, 'not_verified', ?, 'Not verified', ?, NULL, NULL, 'ai', 'none', 'General', ?)
        """, (
            chat_id, user_id, question, search_query, group_key,
            confidence, fallback_msg, now_str
        ))
        question_id = cursor.lastrowid
        conn.commit()

    return {
        "question_id": question_id,
        "status": "not_verified",
        "answer": fallback_msg,
        "confidence": confidence,
        "level": "Not verified",
        "is_verified": False,
        "source": None,
        "office": office_to_show,
        "next_steps": [
            {
                "type": "office_contact",
                "label": f"Contact {office_to_show['name'] if office_to_show else 'Admin Office'}",
                "phone": office_to_show.get("phone", "+91-11-2345-6701") if office_to_show else "",
                "email": office_to_show.get("email", "admin@example.edu") if office_to_show else "",
                "location": office_to_show.get("location", "Administrative Block") if office_to_show else "",
            }
        ],
    }
