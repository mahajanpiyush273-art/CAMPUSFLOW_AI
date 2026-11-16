import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Common stop words to ignore when searching
STOP_WORDS: Set[str] = {
    "a", "about", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "but", "by", "can", "could", "did", "do",
    "does", "for", "from", "had", "has", "have", "he", "her", "here",
    "him", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "me", "my", "no", "not", "of", "on", "or", "our", "out", "she",
    "should", "so", "some", "tell", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "to", "was",
    "we", "were", "what", "when", "where", "which", "who", "whom",
    "why", "will", "with", "would", "you", "your", "give", "please"
}


def clean_and_tokenize(text: str) -> List[str]:
    """Lowercase text and extract meaningful alphanumeric words."""
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def find_best_notice(
    question: str,
    notices: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Search approved notices for the best match to a student's question.

    Returns:
        (best_notice, confidence_score)
        If confidence < 30 or no notices match, returns (None, confidence_score).
    """
    if not notices:
        return None, 0

    keywords = clean_and_tokenize(question)
    if not keywords:
        return None, 0

    total_keywords = len(keywords)
    best_notice: Optional[Dict[str, Any]] = None
    highest_score = 0.0

    for notice in notices:
        title_text = notice.get("title", "").lower()
        category_text = notice.get("category", "").lower()
        body_text = notice.get("text", "").lower()
        full_content = f"{title_text} {category_text} {body_text}"

        matched_count = 0
        title_matches = 0

        for kw in keywords:
            if kw in full_content:
                matched_count += 1
            if kw in title_text:
                title_matches += 1

        if matched_count > 0:
            # Score based on keyword coverage with bonus weight for title matches
            match_ratio = matched_count / total_keywords
            title_bonus = min(0.3, (title_matches / total_keywords) * 0.3)
            raw_score = (match_ratio * 0.7) + title_bonus

            # Scale to 0-100 percentage
            score = min(100.0, raw_score * 100.0)

            if score > highest_score:
                highest_score = score
                best_notice = notice

    confidence = int(round(highest_score))

    # Hackathon threshold: Confidence must be at least 30% to verify
    if confidence >= 30 and best_notice is not None:
        return best_notice, confidence

    return None, confidence
