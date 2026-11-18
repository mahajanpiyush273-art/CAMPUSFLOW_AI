# CampusFlow AI — 5-Minute Live Presentation Script

> **Event:** Aarambhathon Hackathon | **Theme:** AI, Automation & Intelligent Systems  
> **Team:** Axiom | **Presenter:** KK (or Team Lead PM)  
> **Tagline:** *"Ask. Verify. Act."*

---

## Presentation Checklist Before Walking Up
1. Start the server with `python run.py`.
2. Keep Chrome open to `http://127.0.0.1:8000/login`.
3. Open two tabs:
   - **Tab 1:** Student Portal (`student1` / `student123`)
   - **Tab 2:** Admin Portal (`admin1` / `admin123`)

---

## ⏱️ Minute-by-Minute Demo Script

### 0:00 – 1:00 | The Problem & Our Core Promise
- **Talking points:**
  > "Respected judges, every semester campus information is scattered across messy WhatsApp groups, PDF circulars, and physical notice boards. Students miss crucial fee deadlines, ask the same questions repeatedly, and fall prey to rumors.
  >
  > Today, Team Axiom presents **CampusFlow AI** — with one fundamental promise:
  > ***Every campus question gets a verified answer or a clear next step. Never guess. A wrong deadline is worse than 'Not verified'.***"
- **Action:** Show the landing page (`http://127.0.0.1:8000`), highlight the clean, university-branded interface, and click **Student Login**.

---

### 1:00 – 2:30 | The Student "Ask" Experience & Grounded AI
- **Action:** Sign in as `student1` (`student1` / `student123`).
- **Talking points:**
  > "Let's ask a question in natural Hinglish — exactly how students speak."
- **Action:** Type in the search box:
  ```text
  ppt submission ki last date kab hai
  ```
  Press **Enter**.
- **Key visual moments to point out:**
  1. **Animated Confidence Ring:** Point to the pulsating ring showing **High Confidence**. Explain: *"Our grounded verification formula evaluates BM25 keyword rank, notice coverage, and LLM verification."*
  2. **Verified Notice Citation:** Point to the source badge: *"PPT Submission Last Date — Academic Affairs"*.
  3. **Highlighted Evidence Sentence:** Click **View Source Notice** drawer to show the exact sentence extracted from the university circular with dates highlighted.
  4. **Next Steps Action Buttons:** Point out the instant actionable buttons: *Mark Deadline Done* and *View Full Notice*.

- **Action (Follow-up Turn):** In the same chat, type:
  ```text
  can I pay in installments?
  ```
- **Talking points:**
  > "CampusFlow AI maintains multi-turn context. It knows we were talking about campus fees and retrieves the official **Fee Rules & Regulations**, stating tuition fees can be paid in two equal installments with approval."

- **Action (Safety & Out-of-Corpus Fallback):** Type:
  ```text
  where is Dr. Sharma's cabin located?
  ```
- **Talking points:**
  > "Notice what happens when a student asks something not in official notices. **Zero hallucination.** The AI refuses to make up a room number. It clearly states **'Not verified in official notices'**, suggests contacting the Admissions & Dean Office with direct phone and email, and logs the inquiry to the admin review queue."

---

### 2:30 – 3:30 | Student Action Hub: Forms & Deadlines
- **Action:** Click **📝 Official Forms** in the sidebar. Select **Bonafide Certificate Request**.
- **Talking points:**
  > "Finding information is only half the battle. Students need to act. CampusFlow AI includes a 3-step Form Wizard."
- **Key visual moments:**
  1. **Step 1 - Autofill:** Point out the green **"Autofilled from Profile"** badge on Name, Roll Number, Department, and Semester.
  2. **Step 2 - Review:** Click *Review Details*.
  3. **Step 3 - Confirmation Gate:** Point to the mandatory confirmation checkbox. Explain: *"The student must actively confirm before submission."*
  4. **Instant Receipt:** Check the box and click *Submit Application*. Show the generated reference number: `CF-0000X`.
- **Action:** Click **⏰ Deadlines** in the sidebar.
- **Talking points:**
  > "Students track all upcoming semester deadlines grouped by urgency. They can toggle 'Mark as Done' with animated progress bars, silencing reminder alerts."

---

### 3:30 – 4:30 | The Admin Command Center
- **Action:** Switch to Tab 2 (or log in as `admin1` / `admin123`).
- **Talking points:**
  > "Now let's see how university administrators manage notices and guarantee accuracy."
- **Key visual moments:**
  1. **Insights Dashboard:** Show live KPI counters (Total Questions, Verified Rate %, Avg Confidence), the **custom SVG daily questions volume trend chart**, and category distribution.
  2. **Review Queue (Answer Once, Help Everyone):** Click **❓ Review Queue**.
     > "Here are the unanswered questions grouped by AI keywords. An admin types an official verified answer just once. CampusFlow AI publishes a new FAQ notice, indexes it into search, and automatically dispatches notifications to every student who asked!"
  3. **Upload Notice Wizard with AI Conflict Checks:** Click **📤 Upload Document**.
     - Type or paste notice text with conflicting dates (e.g., fee submission before semester registration).
     - Show the **Animated Stepper**: *Reading file -> Extracting dates -> Checking conflicts*.
     - Show the **Blocking Red Flag**: *"🛑 Conflicting deadline date detected"*.
     - Explain: *"Our deterministic validation engine blocks publishing if dates conflict or instructions are incomplete."*
     - Click **Publish Notice** -> Show chunks indexed in FTS5 and scheduled 2-day / 1-day reminders.

---

### 4:30 – 5:00 | Technical Highlights & Conclusion
- **Talking points:**
  > "To summarize our technical architecture:
  > - **Backend:** Python FastAPI with SQLite WAL mode and FTS5 BM25 search.
  > - **Frontend:** 100% Vanilla ES6 and custom CSS tokens — zero heavy frameworks, zero npm dependencies, instant loading.
  > - **Multi-Provider AI:** Groq (gpt-oss-20b), Gemini Flash fallback, with an automatic **offline grounded mode** if internet drops.
  >
  > CampusFlow AI turns scattered campus notices into trusted answers and seamless student actions. Thank you!"

---

## 🛡️ Judge Q&A Contingencies & Technical Answers

### Q1: What happens if your internet connection drops during the demo?
**Answer:** "CampusFlow AI features a resilient multi-tier fallback. If external AI APIs fail or network drops, our circuit breaker seamlessly engages **Offline Mode**. It runs exact text sentence extraction from our SQLite FTS5 database. The student still gets verified notice citations with zero crashes."

### Q2: How do you prevent students from jailbreaking or extracting internal data?
**Answer:** "Every student query passes through our safety filter before touching retrieval. Queries with jailbreak patterns ('ignore previous', 'system prompt') are rejected immediately. Answers are synthesized exclusively from retrieved document chunks with temperature 0.0, strictly prohibiting external fabrication."

### Q3: How do you calculate the confidence score?
**Answer:** "Our confidence formula is deterministic and grounded:  
$$\text{Score} = 45\% \times \text{Keyword Coverage} + 30\% \times \text{BM25 Rank} + 10\% \times \text{Title Match} + 15\% \times \text{Verification}$$  
If a notice has expired, a 15-point penalty is applied, and queries with below 35% keyword coverage are capped below the threshold and marked 'Not verified'."

### Q4: How is student privacy protected during form submissions?
**Answer:** "Passwords use salted PBKDF2 with SHA-256 and 100,000 iterations. Sessions use signed HTTP-only cookies with Lax SameSite protection. Student form data is restricted to authenticated sessions and university administrative staff."
