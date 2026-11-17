"""
CampusFlow AI - Configuration Module
Central settings loaded from environment variables and project defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "campusflow.db"

# Load local .env file if present
load_dotenv(BASE_DIR / ".env")

# Session & Security
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "change-me":
    # Safe ephemeral key for local runs if not configured
    SECRET_KEY = "campusflow-secret-key-32chars-minimum-token-protection"

# LLM Providers & Models
def _parse_list(val: str, default: list[str]) -> list[str]:
    if not val:
        return default
    items = [x.strip() for x in val.split(",") if x.strip()]
    return items or default

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_KEY_2 = os.environ.get("GROQ_API_KEY_2", "")
GROQ_TEXT_MODELS = _parse_list(
    os.environ.get("GROQ_TEXT_MODELS", ""),
    ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
)
GROQ_VISION_MODELS = _parse_list(
    os.environ.get("GROQ_VISION_MODELS", ""),
    ["qwen/qwen3.8-27b"]
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_KEY_2 = os.environ.get("GEMINI_API_KEY_2", "")
GEMINI_MODELS = _parse_list(
    os.environ.get("GEMINI_MODELS", ""),
    ["gemini-2.5-flash", "gemini-1.5-flash"]
)

EXTRA_LLM_BASE_URL = os.environ.get("EXTRA_LLM_BASE_URL", "")
EXTRA_LLM_API_KEY = os.environ.get("EXTRA_LLM_API_KEY", "")
EXTRA_LLM_MODEL = os.environ.get("EXTRA_LLM_MODEL", "")

# Search & Verification Thresholds
try:
    VERIFIED_MIN_CONFIDENCE = int(os.environ.get("VERIFIED_MIN_CONFIDENCE", "40"))
except ValueError:
    VERIFIED_MIN_CONFIDENCE = 40

CONFIDENCE_HIGH = 70
CONFIDENCE_MEDIUM = 50

# Fixed Domain Categories & Document Types
CATEGORIES = [
    "Exam",
    "Fees",
    "Forms & Registration",
    "Events",
    "Hostel",
    "Admission",
    "Academic",
    "General",
]

DOC_TYPES = [
    "notice",
    "circular",
    "handbook",
    "rules",
    "process_guide",
    "event",
    "faq",
]
