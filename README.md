# CampusFlow AI — "Ask. Verify. Act."

> **Aarambhathon Hackathon Project | Team Axiom**  
> *Theme: AI, Automation & Intelligent Systems*  
> *Problem Statement: Smart Campus Query & Action Assistant*

---

## 🎯 What is CampusFlow AI?

Campus information — fee deadlines, exam timetables, registration forms, and events — is scattered across messy WhatsApp chats, dense PDF circulars, and physical notice boards. Students miss critical deadlines, ask the same questions repeatedly, and fall prey to unverified rumors.

**CampusFlow AI** solves this with one uncompromising rule:  
***"Every campus question gets a verified answer or a clear next step. Never guess. A wrong deadline is worse than 'Not verified'."***

- **Students** ask in natural plain English or Hinglish (e.g. *"ppt submission ki last date kab hai"*). They receive answers derived **strictly from approved university notices**, complete with source citations, highlighted evidence text, confidence rings, and one-click action buttons.
- **When Unsure**, the system never hallucinates. It transparently says **"Not verified in official notices"**, shows the exact campus office contact details (phone, email, room), and routes the question to the Admin Review Queue.
- **Action-Oriented:** Includes 3-step official form wizards with profile autofill, deadline compliance trackers, and automated 2-day / 1-day reminder notifications.
- **Admin Command Center:** Provides AI-powered document ingestion, OCR for physical notice photos, deterministic date conflict checks, an "Answer Once, Help Everyone" review queue, and interactive analytics.

---

## 🚀 Quick Start (Windows & PowerShell)

### Prerequisites
- Python 3.10+ (Recommended: Python 3.13)
- Windows PowerShell

### 1. One-Command Launch (Recommended)
Clone the repository and run:

```powershell
# Navigate to project folder
cd CAMPUSFLOW_AI

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Launch application (starts server & opens browser automatically)
python run.py
```

The application will start on `http://127.0.0.1:8000` and automatically open `http://127.0.0.1:8000/login` in your default browser.

---

## 🔑 Demo Accounts

Use these pre-configured accounts to explore the system:

| Role | Username | Password | Full Name / Description |
| :--- | :--- | :--- | :--- |
| **Student** | `student1` | `student123` | Aarav Sharma (Full student profile, CS Sem 6) |
| **Student** | `student2` | `student123` | Priya Patel (Partial profile, EC Sem 4) |
| **Admin** | `admin1` | `admin123` | Admin Office Staff (Full administrative access) |

---

## 🧪 Running the Test Suite (28/28 Benchmarks)

CampusFlow AI includes an automated benchmark test suite evaluating 28 real-world questions across Fees, Exams, Forms, Events, Admissions, Library, Hostel, Contextual Follow-ups, and Safety Injection attempts:

```powershell
python scripts/run_tests.py
```

**Expected Result:**
```text
================================================================================
  CAMPUSFLOW AI - AUTOMATED ACCURACY & SAFETY TEST SUITE
  Evaluating all 28 benchmark questions from Section 11
================================================================================
Loaded 28 test cases from test_questions.csv

TEST RESULTS: 28/28 PASSED (100% Success Rate)
[SUCCESS] ALL 28 TESTS PASSED PERFECTLY!
```
Detailed execution logs are exported to `tests/results.csv`.

---

## 🛠️ Architecture & Tech Stack

```text
CAMPUSFLOW_AI/
├── backend/
│   ├── config.py           # Settings, LLM model lists, and confidence thresholds
│   ├── database.py         # SQLite connection in WAL mode + FTS5 virtual tables
│   ├── security.py         # Salted PBKDF2 hashing, sessions, and role guards
│   ├── llm.py              # Multi-provider LLM router (Groq / Gemini / Offline)
│   ├── prompts.py          # Strict grounded system prompts with zero hallucination
│   ├── ingest.py           # PDF, Word, Image OCR, semantic chunking, and FTS5 sync
│   ├── extraction.py       # AI metadata extraction + deterministic date validators
│   ├── search.py           # Synonym groups, Hinglish dictionary, and BM25 ranking
│   ├── answer.py           # Ask pipeline, confidence formula, and unverified fallback
│   ├── reminders.py        # 2-day / 1-day background reminder notification service
│   ├── seed.py             # 14 sample documents, 5 offices, 4 forms, and demo users
│   ├── main.py             # FastAPI application, lifespan, and static mounting
│   └── routers/
│       ├── auth.py         # Login, logout, identity, and profile endpoints
│       ├── student.py      # Student ask, notices, forms, deadlines, and notifications
│       └── admin.py        # Ingestion, review queue, offices, submissions, and stats
├── frontend/
│   ├── index.html          # Public landing page with role chooser
│   ├── login.html          # Clean sign-in page with role tabs
│   ├── student.html        # Protected Student SPA shell
│   ├── admin.html          # Protected Admin SPA shell
│   └── static/
│       ├── css/
│       │   ├── tokens.css  # Campus color scheme, typography, and spacing tokens
│       │   ├── base.css    # Layout, ambient blurred shapes, and accessibility
│       │   └── components.css # Topbar, cards, tables, wizard stepper, rings, modals
│       └── js/
│           ├── api.js      # Robust fetch client with error handling
│           ├── router.js   # Hash-based SPA router with 150ms transitions
│           ├── ui.js       # Toast notifications, modals, count-up, confidence ring
│           ├── student/    # Dashboard, Ask chat, Info Hub, Forms 3-step wizard
│           └── admin/      # Insights dashboard, Upload wizard, Notices manager
├── scripts/
│   ├── run_tests.py        # 28-question automated accuracy & safety test runner
│   ├── reset_db.py         # Instant database reset and re-seed utility
│   └── check_keys.py       # API key diagnostic tool
├── tests/
│   ├── test_questions.csv  # 28 benchmark evaluation questions
│   └── results.csv         # Exported test results
├── docs/
│   ├── HOW_IT_WORKS.md     # Detailed architecture & confidence formula guide
│   └── ASSUMPTIONS.md      # Engineering design decisions log
├── DEMO.md                 # 5-minute presenter's script for Aarambhathon
├── run.py                  # Single-command launcher script
└── requirements.txt        # Minimal Python dependencies
```

---

## 🎨 Visual Design Tokens & Palette

CampusFlow AI utilizes a purposeful university color palette designed for high legibility:
- **Primary Brand:** `#C53678` (Red-Violet) — Top bar, primary buttons, verified accents.
- **Accent / Alert:** `#FF5841` (Sunset Orange) — Urgent deadline badges, warning tags, error borders.
- **Success:** `#10B981` (Emerald Green) — High confidence rings, confirmed actions, verified badges.
- **Background:** `#FFFFFF` to `#F9E6EE` subtle gradient with ambient blurred circles.
- **Typography:** System font stack (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Inter`, `sans-serif`).

---

## 🛡️ Grounded Verification & Offline Resilience

- **Zero Hallucination:** Temperature is set to `0.0`. Answers are synthesized exclusively from verified notice chunks.
- **Deterministic Confidence:** Evaluates keyword coverage, FTS5 BM25 rank, and title relevance. Unverified queries are capped below the threshold and referred to campus offices.
- **Offline Mode:** If API keys are missing or network drops, CampusFlow AI automatically transitions to exact notice sentence retrieval. **The application never crashes.**

---

## 👥 Team Axiom (Aarambhathon)

- **PM** — Project Lead, Architecture, Full-Stack Backend & Frontend
- **KK** — Live Presenter & Product Showcase
- **Tan** — Data Collection, Campus Verification & Testing
- **ANV** — Database Schema & Relations
