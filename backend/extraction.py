"""
CampusFlow AI - Document Information Extraction & Date Validation Engine
Combines structured LLM parsing with strict deterministic date and conflict validators.
Flags any discrepancies as 'blocking' (must be resolved) or 'warning'.
"""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import CATEGORIES, DOC_TYPES
from backend.llm import chat_json
from backend.prompts import PROMPT_EXTRACTION_SYSTEM

# Common date regex patterns: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD Month YYYY, Month DD YYYY
DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",                                 # 2026-11-25
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",                    # 25/11/2026 or 25-11-2026
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b",  # 25 Nov 2026
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b", # Nov 25, 2026
]

DEADLINE_TRIGGER_WORDS = [
    "last date", "due date", "submit by", "register by", "deadline",
    "submission", "before", "till", "fees due", "closes on"
]

RELATIVE_DATE_PATTERNS = [
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month)\b",
    r"\bcoming\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week)\b",
    r"\btomorrow\b",
    r"\bend\s+of\s+(?:this\s+)?month\b",
    r"\bthis\s+friday\b",
]


def extract_dates_from_text(text: str) -> List[str]:
    """Find all date strings mentioned in text using regex."""
    found = []
    for pat in DATE_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        found.extend(matches)
    return list(dict.fromkeys(found))  # Preserve order, remove duplicates


def parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse various campus date formats into ISO YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # Direct match for YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%b %d %Y", "%B %d %Y", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def run_deterministic_validators(
    fields: Dict[str, Any],
    raw_text: str,
) -> List[Dict[str, str]]:
    """
    Apply strict rules over extracted or edited fields:
    - Checks for missing required dates when deadline keywords exist
    - Detects conflicting deadline dates
    - Verifies deadline is not prior to publish date
    - Flags relative or ambiguous date references
    - Verifies category and department presence
    - Enforces venue and start time for events
    """
    flags: List[Dict[str, str]] = []
    text_lower = raw_text.lower()

    # 1. Very short or unreadable text check
    if len(raw_text.strip()) < 40:
        flags.append({
            "severity": "blocking",
            "message": "Notice text is too short or unreadable (less than 40 characters).",
            "field": "raw_text",
        })

    # 2. Category & Department check
    category = fields.get("category")
    if not category or category not in CATEGORIES:
        flags.append({
            "severity": "warning",
            "message": "Category is missing or not one of the approved campus categories.",
            "field": "category",
        })

    department = fields.get("department")
    if not department or not str(department).strip():
        flags.append({
            "severity": "warning",
            "message": "Department or issuing office is not specified.",
            "field": "department",
        })

    # 3. Publish and Expiry Date Consistency
    pub_date_str = parse_date_to_iso(str(fields.get("publish_date") or ""))
    exp_date_str = parse_date_to_iso(str(fields.get("expiry_date") or ""))

    if pub_date_str and exp_date_str:
        try:
            pub_d = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
            exp_d = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            if exp_d < pub_d:
                flags.append({
                    "severity": "blocking",
                    "message": f"Expiry date ({exp_date_str}) cannot be earlier than publish date ({pub_date_str}).",
                    "field": "expiry_date",
                })
        except Exception:
            pass

    # 4. Deadlines validation
    deadlines = fields.get("deadlines", [])
    has_deadline_keywords = any(kw in text_lower for kw in DEADLINE_TRIGGER_WORDS)

    if has_deadline_keywords and not deadlines:
        flags.append({
            "severity": "blocking",
            "message": "Notice text mentions deadline/submission keywords, but no explicit deadline date was detected.",
            "field": "deadlines",
        })

    seen_dates: List[Tuple[str, str]] = []
    for dl in deadlines:
        dl_label = dl.get("label", "Deadline")
        raw_dl_date = dl.get("date")
        iso_dl_date = parse_date_to_iso(str(raw_dl_date or ""))

        if not iso_dl_date:
            flags.append({
                "severity": "blocking",
                "message": f"Deadline '{dl_label}' has an invalid or unparseable date '{raw_dl_date}'.",
                "field": "deadlines",
            })
            continue

        # Check if deadline is before publish date
        if pub_date_str:
            try:
                dl_d = datetime.strptime(iso_dl_date, "%Y-%m-%d").date()
                pub_d = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                if dl_d < pub_d:
                    flags.append({
                        "severity": "blocking",
                        "message": f"Deadline date ({iso_dl_date}) cannot be earlier than publish date ({pub_date_str}).",
                        "field": "deadlines",
                    })
            except Exception:
                pass

        seen_dates.append((dl_label, iso_dl_date))

    # Detect conflicting dates for the same deadline or contradictory statements
    if len(seen_dates) > 1:
        dates_set = {d[1] for d in seen_dates}
        # If text has multiple conflicting phrases like 'submit by D+6' and 'submission D+8'
        if len(dates_set) > 1 and any("submission" in d[0].lower() or "last date" in d[0].lower() for d in seen_dates):
            date_list = ", ".join(sorted(dates_set))
            flags.append({
                "severity": "blocking",
                "message": f"Conflicting submission dates detected ({date_list}). Please verify which is final.",
                "field": "deadlines",
            })

    # 5. Check for relative/unclear dates in text
    for pat in RELATIVE_DATE_PATTERNS:
        match = re.search(pat, text_lower)
        if match:
            flags.append({
                "severity": "warning",
                "message": f"Relative or ambiguous date '{match.group(0)}' found in text. Please replace with an exact calendar date.",
                "field": "raw_text",
            })
            break

    # 6. Event details validation
    if fields.get("doc_type") == "event":
        event_info = fields.get("event") or {}
        event_start = event_info.get("start")
        venue = event_info.get("venue")
        if not event_start or not str(event_start).strip():
            flags.append({
                "severity": "blocking",
                "message": "Event document must specify an event start date/time.",
                "field": "event.start",
            })
        if not venue or not str(venue).strip():
            flags.append({
                "severity": "blocking",
                "message": "Event document must specify a physical or virtual venue.",
                "field": "event.venue",
            })

    return flags


def extract_and_validate_document(raw_text: str, default_doc_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Run LLM extraction on notice text, then apply deterministic validators.
    Returns extracted fields + list of AI/deterministic flags.
    """
    extracted_fields: Dict[str, Any] = {}
    today_iso = date.today().isoformat()

    # 1. Attempt LLM JSON extraction
    user_prompt = f"Notice Text:\n{raw_text}\n\nToday's Date: {today_iso}"
    llm_result, provider, model = chat_json(
        system_prompt=PROMPT_EXTRACTION_SYSTEM,
        user_prompt=user_prompt,
        timeout=25.0,
    )

    if llm_result and isinstance(llm_result, dict):
        extracted_fields = llm_result
    else:
        # Fallback heuristic extraction in offline mode
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        first_line = lines[0] if lines else "Campus Notice"
        dates = extract_dates_from_text(raw_text)
        first_iso = parse_date_to_iso(dates[0]) if dates else None

        extracted_fields = {
            "title": first_line[:100],
            "doc_type": default_doc_type or "notice",
            "category": "General",
            "department": None,
            "publish_date": today_iso,
            "expiry_date": None,
            "summary": raw_text[:200].replace("\n", " "),
            "deadlines": [{"label": "Notice Deadline", "date": first_iso, "time": None, "evidence": dates[0]}] if first_iso else [],
            "event": {"start": None, "venue": None, "registration_url": None},
            "contacts": [],
            "issues": [],
        }

    # Normalize fields
    if default_doc_type:
        extracted_fields["doc_type"] = default_doc_type
    if not extracted_fields.get("publish_date"):
        extracted_fields["publish_date"] = today_iso

    # 2. Run deterministic validators
    flags = run_deterministic_validators(extracted_fields, raw_text)

    return {
        "fields": extracted_fields,
        "flags": flags,
        "provider": provider,
        "model": model,
    }
