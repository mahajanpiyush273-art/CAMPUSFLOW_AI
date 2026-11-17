# CampusFlow AI — Architecture and Design Decisions (Assumptions Log)

This document records all decisions made to keep the system simple, maintainable, robust, and aligned with the Aarambhathon problem statement.

## 1. Authentication and Session Management
- **Decision:** Use Starlette's signed cookie `SessionMiddleware` with `HttpOnly` and `SameSite=Lax`.
- **Reason:** Requires no external session store or Redis. It works natively in FastAPI on Windows and protects endpoints without client token complexity.
- **Passwords:** Salted PBKDF2 with SHA-256 (standard Python `hashlib`), eliminating external cryptography compilation issues on Windows.

## 2. Model Routing & AI Fallback
- **Decision:** Groq is the primary provider (`openai/gpt-oss-20b`, fallback `openai/gpt-oss-120b`). Vision utilizes `qwen/qwen3.8-27b` on Groq, with Gemini Flash as secondary fallback.
- **Offline Mode:** If all keys are missing, expired, or rate-limited, the system seamlessly transitions to rule-based keyword extraction and exact text excerpt matching. The app never crashes or raises unhandled exceptions when AI services are unreachable.

## 3. Database & Full Text Search (FTS5)
- **Decision:** SQLite with Write-Ahead Logging (`WAL` mode), foreign key enforcement enabled, and SQLite `FTS5` virtual tables for document chunks.
- **Reason:** Built into Python's `sqlite3`, cross-platform, zero setup, and fast BM25 ranking without external vector databases.

## 4. Frontend Architecture
- **Decision:** Vanilla ES6 modules with hash routing (`#/dashboard`, `#/ask`, etc.) and CSS custom properties defined in `tokens.css`.
- **Reason:** Avoids any Node.js build pipeline, npm scripts, or bundler complexity while providing instantaneous SPA responsiveness, offline visual styling, and clear code organization.
