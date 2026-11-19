# CampusFlow AI — Beginner's Guide to Every File

Welcome to **CampusFlow AI**! If you are new to programming or this project, this guide explains what the project does and what **every single file** in the codebase does in plain, simple English.

---

## 🏫 The Big Picture: What is CampusFlow AI?

Imagine your university campus. Every week, different departments post circulars, exam schedules, fee payment deadlines, and application forms. Students get confused, miss deadlines, or have to run from office to office asking questions.

**CampusFlow AI** fixes this:
1. **For Staff / Admins:** They upload an official circular (PDF, image, Word doc) or post an application form link. An AI automatically reads it, extracts important dates, flags any conflicts, and indexes it.
2. **For Students:** They can type questions in plain English or Hinglish (e.g. *"When is the mid-term exam fee deadline?"*). The AI searches official notices and gives an exact, verified answer with citations and next steps.

---

## 🧭 How The Project Is Structured (A Simple Analogy)

Think of CampusFlow AI like a **modern university library & helpdesk**:
- **Frontend (`frontend/`):** The front desk and computer screens where students and staff click, type, and read.
- **Backend (`backend/`):** The offices behind the counter where staff verify documents, run searches, and talk to AI.
- **Database (`campusflow.db`):** The secure filing cabinet where all notices, dates, users, and forms are stored.
- **AI Brains (`backend/llm.py` & `backend/vision.py`):** The smart assistants that read scanned papers and answer questions.

---

## 📁 Root Files (Project Foundation)

| File | What it does in simple words |
| :--- | :--- |
| **`run.py`** | **The Start Button.** When you type `python run.py`, this file turns on the web server (Uvicorn), checks your database, and gets the app ready at `http://localhost:8000`. |
| **`requirements.txt`** | **The Shopping List.** A list of all external Python libraries the project needs (like `fastapi` for the web server, `groq` and `google-genai` for AI, and `pdfplumber` for reading PDFs). |
| **`.env.example`** | **The Secret Keys Template.** A sample file showing where to put secret configuration settings, like your Groq or Gemini API keys. (You copy this to `.env`). |
| **`.gitignore`** | **The Do-Not-Upload List.** Tells Git which files to never upload to GitHub (like passwords, `.env`, temporary caches, and database files). |
| **`README.md`** | **The Project Brochure.** The main project overview on GitHub explaining how to install, configure, and use CampusFlow AI. |
| **`DEMO.md`** | **The Walkthrough Guide.** Step-by-step instructions for demonstrating CampusFlow AI live (sample logins, test queries, and features). |

---

## ⚙️ Backend Files (`backend/`) — The Brains & Engine

The backend is built in **Python** using the **FastAPI** web framework.

### Core Backend Files

| File | What it does in simple words |
| :--- | :--- |
| **`backend/main.py`** | **The Receptionist & Gatekeeper.** The main entry point of the backend. It sets up web routes, manages security headers (cache prevention), and serves the frontend HTML and static files. |
| **`backend/config.py`** | **The Settings Binder.** Reads environment variables and API keys from `.env` (like Groq API key, Gemini API key, session secret, and database path). |
| **`backend/database.py`** | **The Filing Cabinet Master.** Manages the SQLite database (`campusflow.db`). It creates tables (notices, users, deadlines, offices), runs migrations, and handles read/write queries safely. |
| **`backend/security.py`** | **The Security Guard.** Handles password hashing (making passwords safe using PBKDF2/SHA-256) and generates encrypted session cookies so users stay logged in securely. |
| **`backend/seed.py`** | **The Setup Starter Pack.** Automatically pre-populates the database on first run with demo accounts (student and admin), sample university offices, and initial verified campus notices. |
| **`backend/search.py`** | **The Superfast Index / Librarian.** Uses SQLite `FTS5` (Full-Text Search) with BM25 ranking to search through thousands of notice words in less than 5 milliseconds. |
| **`backend/llm.py`** | **The Smart AI Router.** Connects to AI models. It first tries Groq for lightning-fast answers; if Groq is busy or lacks quota, it automatically falls back to Google Gemini. If offline, it uses smart keyword matching. |
| **`backend/prompts.py`** | **The AI Scriptbook.** Contains the exact system prompts and instructions given to the AI (e.g. *"Answer only based on the official text", "Never hallucinate", "Extract deadlines in YYYY-MM-DD format"*). |
| **`backend/extraction.py`** | **The Document Analyzer.** Reads raw notice text, extracts title, department, category, and deadlines, and checks if a new notice conflicts with an older one. |
| **`backend/vision.py`** | **The AI Eyes (OCR).** Uses AI vision to read scanned circulars, photos of notice boards, or smartphone pictures of printed college papers. |
| **`backend/answer.py`** | **The Q&A Machine.** When a student asks a question, this file coordinates everything: finds relevant notices via `search.py`, asks `llm.py` to synthesize a clear answer, and calculates a confidence score. |
| **`backend/reminders.py`** | **The Alarm Clock.** A background task that checks deadlines (e.g. fees due in 2 days or 1 day) and creates notifications so students never miss an important date. |
| **`backend/ai.py`** | **The AI Hub Utility.** Helper functions that tie together text extraction, prompt formatting, and fallback safety routines. |

---

### Backend Routers (`backend/routers/`) — The Department Counters

FastAPI uses "routers" to organize API endpoints into clean groups:

| File | What it does in simple words |
| :--- | :--- |
| **`backend/routers/auth.py`** | **The ID & Badge Office.** Handles user registration, logging in, logging out, checking current user role (`/api/me`), and demo credential access. |
| **`backend/routers/student.py`** | **The Student Help Desk API.** Serves student endpoints: asking questions (`/api/student/ask`), viewing the notice feed, bookmarking notices, and listing downloadable/fillable forms. |
| **`backend/routers/admin.py`** | **The Dean & Admin Office API.** Handles staff actions: uploading new documents (`/api/admin/upload`), publishing direct form links (`/api/admin/forms/publish`), editing notices, viewing analytics, and managing office contact cards. |

---

## 🎨 Frontend Files (`frontend/`) — What Users See & Click

The frontend is built using **Vanilla HTML5, Modern CSS, and modular ES6 JavaScript** — no complex frameworks like React or Node build steps needed!

### Web Pages (HTML)

| File | What it does in simple words |
| :--- | :--- |
| **`frontend/index.html`** | **The Landing Page.** The public homepage that visitors see first. Displays the university hero banner, features, and direct role-based login cards. |
| **`frontend/login.html`** | **The Login Gate.** The sign-in screen where students and faculty enter their email and password. |
| **`frontend/student.html`** | **The Student Portal Shell.** The container for the student web app (top bar, navigation links, and dynamic view area). |
| **`frontend/admin.html`** | **The Admin Portal Shell.** The container for the faculty/admin web app (sidebar, analytics, document uploader, and review queue). |

---

### Stylesheets (`frontend/static/css/`)

| File | What it does in simple words |
| :--- | :--- |
| **`frontend/static/css/tokens.css`** | **The Color & Style Rules.** Defines design variables: university colors (brand pinks, purples, oranges), border radiuses, shadows, font sizes, and dark/light mode tokens. |
| **`frontend/static/css/base.css`** | **The Foundation.** Sets up page reset, typography, ambient background glows, and overall page layouts. |
| **`frontend/static/css/components.css`** | **The Building Blocks.** Styles all reusable UI parts: buttons, cards, modals, toast alerts, form inputs, tables, and stepper indicators. |

---

### Shared Frontend Scripts (`frontend/static/js/`)

| File | What it does in simple words |
| :--- | :--- |
| **`frontend/static/js/api.js`** | **The Telephone Wire.** Makes HTTP calls (`fetch`) to the backend with automatic JSON conversion and error handling. |
| **`frontend/static/js/router.js`** | **The Traffic Director (SPA Router).** Listens to browser URL hash changes (like `#/dashboard` or `#/upload`) and swaps the view smoothly without reloading the entire page. |
| **`frontend/static/js/ui.js`** | **The UI Magician.** Handles popup notifications (toasts), modal dialogs, loading skeletons, and interactive animations. |

---

### Student Portal Views (`frontend/static/js/student/`)

| File | What it does in simple words |
| :--- | :--- |
| **`frontend/static/js/student/app.js`** | **Student App Conductor.** Verifies the student is logged in, initializes the navigation router, and hooks up the bottom navigation bar. |
| **`frontend/static/js/student/dashboard.js`** | **Student Dashboard View.** Shows the student's personal feed: urgent deadlines, new notices, and pinned university circulars. |
| **`frontend/static/js/student/ask.js`** | **Ask CampusFlow AI Screen.** The core student interface: lets students ask questions, shows verified answers, citations, contact cards, and follow-up chips. |
| **`frontend/static/js/student/forms.js`** | **Application Forms Screen.** Lists official university application links (bonafide certificate, hostel change, fee waiver) with direct apply buttons. |
| **`frontend/static/js/student/info.js`** | **Campus Offices Directory.** A searchable directory of campus offices (Accounts, Registrar, Library, Exam Cell) with timings, locations, and contact info. |

---

### Admin Portal Views (`frontend/static/js/admin/`)

| File | What it does in simple words |
| :--- | :--- |
| **`frontend/static/js/admin/app.js`** | **Admin App Conductor.** Verifies staff permissions, connects admin navigation routes, and manages review badge counts. |
| **`frontend/static/js/admin/dashboard.js`** | **Admin Insights Dashboard.** Displays live statistics: total active notices, upcoming deadlines, query volume, and student activity trends. |
| **`frontend/static/js/admin/upload.js`** | **Document Upload Wizard.** A 4-step wizard for faculty to upload documents or post direct form links, preview AI extraction, and publish to campus. |
| **`frontend/static/js/admin/manage.js`** | **Notice Manager & Review Queue.** Allows staff to view all published notices, edit them, approve flagged items, and update campus office contact info. |

---

## 🛠️ Testing & Utility Scripts (`scripts/` & `tests/`)

| File | What it does in simple words |
| :--- | :--- |
| **`scripts/check_keys.py`** | **The Key Checker.** A quick command-line tool that tests whether your Groq and Google Gemini API keys are active and working. |
| **`scripts/reset_db.py`** | **The Reset Button.** Cleans up the database and re-runs `seed.py` to restore a clean, fresh state for demonstrations. |
| **`scripts/run_tests.py`** | **The Automated Examiner.** Runs automated tests by feeding student questions into CampusFlow AI and checking the accuracy of the answers. |
| **`tests/test_questions.csv`** | **The Question Bank.** A spreadsheet of sample student questions (fees, exams, hostel, events) used by `run_tests.py` to verify accuracy. |

---

## 📚 Technical Documentation (`docs/`)

| File | What it does in simple words |
| :--- | :--- |
| **`docs/HOW_IT_WORKS.md`** | **Technical Deep Dive.** A detailed technical explanation of the 5-stage AI pipeline, BM25 ranking, and database architecture. |
| **`docs/ASSUMPTIONS.md`** | **Engineering Decisions.** Explains why certain design choices were made (e.g. why SQLite WAL mode was picked, fallback LLM hierarchy). |
| **`docs/BEGINNER_GUIDE.md`** | **This Document!** The simple, friendly file-by-file guide for beginners and newcomers. |

---

*CampusFlow AI — Ask. Verify. Act.*
