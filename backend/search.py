"""
CampusFlow AI - Semantic Search & Verification Confidence Scoring Engine
Combines SQLite FTS5 BM25 retrieval, campus synonym expansion,
Hinglish keyword translation, expired notice penalties, and grounded confidence scoring.
"""

from datetime import date, datetime
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, VERIFIED_MIN_CONFIDENCE
from backend.database import get_connection
from backend.ingest import is_document_expired

# Standard English stop words
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me", "more",
    "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves", "tell", "give", "please",
    "want", "know", "can"
}

# Campus domain synonym mappings
SYNONYM_GROUPS: List[Set[str]] = [
    {"deadline", "last date", "due date", "submit by", "submission", "closes on", "kab tak"},
    {"fee", "fees", "payment", "fine", "waiver", "challan", "receipt", "jama", "jama karna", "cost"},
    {"form", "application", "request", "registration", "apply"},
    {"hostel", "room", "warden", "curfew", "mess", "accommodation", "room change"},
    {"exam", "exams", "examination", "mid-term", "midterm", "final", "test", "timetable", "schedule"},
    {"ppt", "presentation", "slides", "project", "final year"},
    {"certificate", "bonafide", "study certificate", "proof"},
    {"event", "workshop", "session", "orientation", "fest", "club"},
    {"attendance", "minimum attendance", "medical leave", "conduct", "rules"},
    {"curfew", "timings", "gate timing", "10:00 pm", "late entry"},
    {"working day", "teaching day", "timetable", "classes", "saturday"},
    {"volunteer", "volunteering", "cultural fest"},
]

# Common Hinglish conversational words to English campus terms
HINGLISH_MAP: Dict[str, str] = {
    "kab": "when",
    "kahan": "where",
    "kaha": "where",
    "kitna": "how much",
    "kitne": "how many",
    "kaise": "how",
    "kya": "what",
    "tak": "until deadline",
    "jama": "pay submit",
    "karni": "",
    "karna": "",
    "hai": "",
    "ho": "",
    "raha": "",
    "rahi": "",
    "chahiye": "need require",
    "dena": "give submit",
    "milega": "get receive",
    "milta": "get receive",
    "batao": "tell",
}


def clean_and_tokenize(text: str) -> List[str]:
    """Extract alphanumeric words from query, excluding standard stop words."""
    words = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def expand_query_with_synonyms(keywords: List[str]) -> List[str]:
    """Expand keywords with campus synonym groups and Hinglish translations."""
    expanded: Set[str] = set(keywords)

    # 1. Check Hinglish mappings
    for kw in keywords:
        if kw in HINGLISH_MAP:
            translated = HINGLISH_MAP[kw].split()
            expanded.update(t for t in translated if t and t not in STOP_WORDS)

    # 2. Check campus domain synonym groups
    for group in SYNONYM_GROUPS:
        # Check if any keyword matches a group item exactly or as a token in a multi-word phrase
        if any(any(kw == syn or kw in syn.split() for syn in group) for kw in keywords):
            # Add all primary single-word synonyms from this group
            for syn in group:
                for token in syn.split():
                    if token not in STOP_WORDS and len(token) > 2:
                        expanded.add(token)

    return list(expanded)


def search_fts5_chunks(
    query_text: str,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """
    Query the SQLite FTS5 virtual table for published document chunks matching the query.
    Returns matched chunks with document metadata and BM25 rank score.
    """
    raw_keywords = clean_and_tokenize(query_text)
    if not raw_keywords:
        return []

    expanded_keywords = expand_query_with_synonyms(raw_keywords)
    if not expanded_keywords:
        expanded_keywords = raw_keywords

    # Format query for FTS5 (use OR between terms to allow flexible partial matches)
    safe_terms = [re.sub(r"[^\w]", "", kw) for kw in expanded_keywords if len(kw) > 1]
    safe_terms = [t for t in safe_terms if t]
    if not safe_terms:
        return []

    # Construct FTS query string: term1 OR term2 OR ...
    fts_match_query = " OR ".join(safe_terms)

    with get_connection() as conn:
        cursor = conn.cursor()
        # Query chunks_fts joined with documents and chunks tables
        # rank is FTS5's built-in BM25 score (more negative is better match)
        sql = """
            SELECT
                fts.chunk_id,
                CAST(fts.document_id AS INTEGER) AS document_id,
                fts.heading,
                fts.text AS chunk_text,
                d.title AS doc_title,
                d.doc_type,
                d.category,
                d.department,
                d.publish_date,
                d.expiry_date,
                d.office_id,
                d.related_form_id,
                d.status,
                d.is_sample,
                d.raw_text AS full_doc_text,
                fts.rank AS bm25_score
            FROM chunks_fts fts
            JOIN documents d ON d.id = CAST(fts.document_id AS INTEGER)
            WHERE chunks_fts MATCH ? AND d.status = 'published'
            ORDER BY fts.rank ASC
            LIMIT ?;
        """
        try:
            rows = cursor.execute(sql, (fts_match_query, limit * 2)).fetchall()
        except Exception:
            # Fallback to simple title/text LIKE if FTS expression has syntax quirks
            sql_fallback = """
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    c.heading,
                    c.text AS chunk_text,
                    d.title AS doc_title,
                    d.doc_type,
                    d.category,
                    d.department,
                    d.publish_date,
                    d.expiry_date,
                    d.office_id,
                    d.related_form_id,
                    d.status,
                    d.is_sample,
                    d.raw_text AS full_doc_text,
                    -10.0 AS bm25_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'published' AND (
                    d.title LIKE ? OR c.text LIKE ?
                )
                LIMIT ?;
            """
            first_kw = safe_terms[0] if safe_terms else query_text
            rows = cursor.execute(sql_fallback, (f"%{first_kw}%", f"%{first_kw}%", limit)).fetchall()

    results: List[Dict[str, Any]] = []
    seen_chunks: Set[int] = set()

    for r in rows:
        cid = r["chunk_id"]
        if cid in seen_chunks:
            continue
        seen_chunks.add(cid)

        item = dict(r)
        item["old"] = is_document_expired(item.get("expiry_date"))
        results.append(item)

    # Rank matches by BM25 score with an exact query keyword hit bonus and mild penalty for expired (OLD) documents
    for item in results:
        base_rank = float(item.get("bm25_score", 0.0))
        chunk_content = f"{item.get('doc_title', '')} {item.get('heading', '')} {item.get('chunk_text', '')}".lower()
        title_lower = str(item.get("doc_title", "")).lower()

        chunk_tokens = set(clean_and_tokenize(chunk_content))
        title_tokens = set(clean_and_tokenize(title_lower))

        # Count how many original query keywords appear in chunk or title
        raw_hits = sum(1 for kw in raw_keywords if kw in chunk_tokens)
        title_hits = sum(1 for kw in raw_keywords if kw in title_tokens)

        # More negative adjusted_rank means higher relevance in ascending sort
        score_rank = base_rank - (raw_hits * 3.5) - (title_hits * 5.0)

        if item.get("old"):
            # Weaken expired notice rank
            score_rank = score_rank * 0.6 if score_rank < 0 else score_rank * 1.4

        item["adjusted_rank"] = score_rank

    results.sort(key=lambda x: x["adjusted_rank"])
    return results[:limit]


def compute_confidence_score(
    question: str,
    top_chunk: Dict[str, Any],
    llm_answered_ok: bool,
    is_offline: bool = False,
) -> Tuple[int, str]:
    """
    Compute confidence score (0-100) and confidence tier level.
    Formula (Section 8.4):
    coverage   = fraction of question keywords found in best chunk + title (0-1)
    bm25_norm  = squashed BM25 score (0-1)
    title_hit  = 1 if keyword in title, else 0
    llm_ok     = 1 if LLM answered from text, 0 if it could not, 1 in offline mode when coverage >= 50%
    confidence = round(100 * (0.45*coverage + 0.30*bm25_norm + 0.10*title_hit + 0.15*llm_ok))
    minus 15 if expired (OLD)
    """
    raw_keywords = clean_and_tokenize(question)
    expanded = expand_query_with_synonyms(raw_keywords) or raw_keywords

    chunk_content = f"{top_chunk.get('doc_title', '')} {top_chunk.get('heading', '')} {top_chunk.get('chunk_text', '')}".lower()
    title_lower = str(top_chunk.get("doc_title", "")).lower()

    chunk_tokens = set(clean_and_tokenize(chunk_content))
    title_tokens = set(clean_and_tokenize(title_lower))

    # 1. Coverage using token matching to prevent false substring collisions
    matched_kws = sum(1 for kw in raw_keywords if kw in chunk_tokens)
    matched_expanded = sum(1 for kw in expanded if kw in chunk_tokens)

    total_raw = max(len(raw_keywords), 1)
    raw_coverage = min(1.0, matched_kws / total_raw)
    expanded_coverage = min(1.0, matched_expanded / max(len(expanded), 1))

    coverage = max(raw_coverage, 0.7 * expanded_coverage + 0.3 * raw_coverage)

    # Low coverage penalty: if fewer than 35% of core query keywords are in the notice,
    # the document does not answer the student's question!
    if raw_coverage < 0.35 and len(raw_keywords) >= 3:
        score = int(round(raw_coverage * 60))
        return score, "Not verified"

    # 2. BM25 Norm
    raw_bm25 = abs(float(top_chunk.get("bm25_score", -5.0)))
    bm25_norm = min(1.0, math.tanh(raw_bm25 / 10.0))

    # 3. Title Hit
    title_hit = 1.0 if any(kw in title_tokens for kw in raw_keywords) else 0.0

    # 4. LLM OK weight
    if is_offline:
        llm_val = 1.0 if (raw_coverage >= 0.5 or matched_kws >= 2) else 0.5
    else:
        llm_val = 1.0 if llm_answered_ok else 0.0

    # Calculate raw score
    raw_score = (0.45 * coverage) + (0.30 * bm25_norm) + (0.10 * title_hit) + (0.15 * llm_val)
    score = int(round(100.0 * raw_score))

    # Penalty for expired notice
    if top_chunk.get("old"):
        score = max(0, score - 15)

    # Clamp between 0 and 100
    score = max(0, min(100, score))

    # Determine confidence level
    if score >= CONFIDENCE_HIGH:
        level = "High"
    elif score >= CONFIDENCE_MEDIUM:
        level = "Medium"
    elif score >= VERIFIED_MIN_CONFIDENCE:
        level = "Low"
    else:
        level = "Not verified"

    return score, level
