"""
CampusFlow AI - Ingestion & Chunking Engine
Extracts text from TXT, MD, PDF, DOCX, and images.
Chunks content semantically and manages the SQLite FTS5 index.
"""

from datetime import date, datetime
import io
from pathlib import Path
from typing import List, Optional, Tuple

import docx
from pypdf import PdfReader

from backend.database import get_connection
from backend.llm import chat_vision


def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str] = None,
) -> str:
    """
    Extract readable text from uploaded file based on extension.
    Supports .txt, .md, .pdf, .docx, and image formats (.jpg, .jpeg, .png).
    """
    ext = Path(filename).suffix.lower()

    if ext in [".txt", ".md"]:
        try:
            return file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore").strip()

    elif ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt and txt.strip():
                    pages_text.append(txt.strip())
            
            full_text = "\n\n".join(pages_text).strip()
            if not full_text:
                raise ValueError("This PDF contains no selectable text (it may be scanned). Please upload as an image or paste the text directly.")
            return full_text
        except Exception as e:
            if "scanned" in str(e).lower():
                raise e
            raise ValueError(f"Could not read PDF document: {str(e)}")

    elif ext == ".docx":
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            parts = []
            # Extract paragraphs
            for p in doc.paragraphs:
                if p.text and p.text.strip():
                    parts.append(p.text.strip())
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        parts.append(" | ".join(row_texts))
            full_docx = "\n\n".join(parts).strip()
            if not full_docx:
                raise ValueError("Word document is empty.")
            return full_docx
        except Exception as e:
            raise ValueError(f"Could not read Word document: {str(e)}")

    elif ext in [".png", ".jpg", ".jpeg"]:
        detected_mime = mime_type or ("image/png" if ext == ".png" else "image/jpeg")
        extracted_text, provider, model = chat_vision(
            prompt=(
                "Extract all readable text from this campus notice image accurately. "
                "Preserve all headings, dates, announcements, rules, departments, and contact info. "
                "Return only the extracted text without introductory or concluding remarks."
            ),
            image_bytes=file_bytes,
            mime_type=detected_mime,
        )
        if not extracted_text or not extracted_text.strip():
            raise ValueError("Could not extract readable text from notice image. Please type the text manually.")
        return extracted_text.strip()

    else:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed: .pdf, .docx, .txt, .md, .png, .jpg, .jpeg")


def chunk_document(raw_text: str, document_title: str = "", max_chars: int = 700, overlap: int = 80) -> List[Tuple[str, str]]:
    """
    Split text into semantic chunks of ~500-800 characters with nearest heading attached.
    Always includes the document title in context.
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    if not lines:
        return [(document_title or "Notice", raw_text)]

    current_heading = lines[0] if len(lines[0]) < 80 else (document_title or "Notice")
    chunks = []
    current_buf = []
    current_len = 0

    for line in lines:
        if line.startswith("#") or line.endswith(":") or (len(line) < 50 and line.isupper()):
            current_heading = line.lstrip("#").strip()

        current_buf.append(line)
        current_len += len(line) + 1

        if current_len >= max_chars:
            chunk_body = " ".join(current_buf)
            chunks.append((current_heading, chunk_body))
            # Keep overlap words
            overlap_words = chunk_body.split()[-12:]
            current_buf = [" ".join(overlap_words)]
            current_len = len(current_buf[0])

    if current_buf:
        chunk_body = " ".join(current_buf)
        if not chunks or chunk_body != chunks[-1][1]:
            chunks.append((current_heading, chunk_body))

    return chunks


def index_document(document_id: int) -> int:
    """
    Index a published document into the chunks table and FTS5 search index.
    Removes old chunks and recreates new ones.
    Returns the number of chunks indexed.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        doc = cursor.execute(
            "SELECT id, title, raw_text, status FROM documents WHERE id = ?",
            (document_id,)
        ).fetchone()

        if not doc:
            return 0

        # Delete existing chunks and FTS entries
        cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        cursor.execute("DELETE FROM chunks_fts WHERE document_id = ?", (str(document_id),))

        # Only index if published
        if doc["status"] != "published":
            conn.commit()
            return 0

        chunks = chunk_document(doc["raw_text"], document_title=doc["title"])
        for idx, (heading, text_part) in enumerate(chunks):
            cursor.execute("""
                INSERT INTO chunks (document_id, chunk_index, heading, text)
                VALUES (?, ?, ?, ?)
            """, (document_id, idx, heading, text_part))
            chunk_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO chunks_fts (title, heading, text, chunk_id, document_id)
                VALUES (?, ?, ?, ?, ?)
            """, (doc["title"], heading, text_part, str(chunk_id), str(document_id)))

        conn.commit()
        return len(chunks)


def remove_document_index(document_id: int) -> None:
    """Remove a document from chunks and FTS5 search index on unpublish or deletion."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        cursor.execute("DELETE FROM chunks_fts WHERE document_id = ?", (str(document_id),))
        conn.commit()


def is_document_expired(expiry_date: Optional[str]) -> bool:
    """Check if a document's expiry date has passed compared to today."""
    if not expiry_date:
        return False
    try:
        exp_d = datetime.strptime(expiry_date[:10], "%Y-%m-%d").date()
        return exp_d < date.today()
    except Exception:
        return False
