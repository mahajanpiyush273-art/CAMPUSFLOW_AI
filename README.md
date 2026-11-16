# CampusFlow AI

> **"Ask. Verify. Act."**

CampusFlow AI is an intelligent campus information assistant built for Aarambhathon. It enables students to ask questions in plain language and receive accurate answers derived strictly from verified university notices, complete with source citations and confidence scores.

When an inquiry has no matching approved notice (confidence under 30%), the assistant marks the query as **"Not verified"** and directs the student to the official administrative office.

---

## Quick Start

1. **Activate Virtual Environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Set Your API Key:**
   ```powershell
   $env:GROQ_API_KEY = "your-groq-api-key"
   ```

3. **Run Application:**
   ```powershell
   python -m uvicorn backend.main:app --reload
   ```
   Visit `http://127.0.0.1:8000` in your browser.

---

## Demo Accounts

- **Student Area:** `student1` / `student123`
- **Admin Dashboard:** `admin1` / `admin123`

---

## Project Structure

- `backend/main.py`: FastAPI routes for auth, student queries, notice uploads, and image reading.
- `backend/database.py`: SQLite storage (`campusflow.db`) for campus notices.
- `backend/search.py`: Keyword-matching search engine with confidence calculation.
- `backend/vision.py`: Multimodal notice extraction via Groq (`qwen/qwen3.8-27b`) or Gemini Flash.
- `backend/ai.py`: Hallucination-free answer generation via Groq (`openai/gpt-oss-120b`).
- `frontend/login.html`: Two-step role chooser and login interface.
- `frontend/student.html`: Student question portal with verified answers and source cards.
- `frontend/admin.html`: Notice management dashboard for typed and image-based notices.
