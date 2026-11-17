"""
CampusFlow AI - Database Seeding Module
Populates the database with realistic sample campus notices, events, handbooks,
offices, forms, demo user accounts, and deadlines calculated relative to today (D).
All sample documents have is_sample = 1 and are clearly marked SAMPLE DATA.
"""

import hashlib
import json
import secrets
from datetime import date, datetime, timedelta
from typing import List, Tuple

from backend.database import get_connection, reindex_document_fts


def hash_password(password: str) -> str:
    """Hash password using standard library PBKDF2-HMAC-SHA256 with random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash."""
    try:
        salt, key_hex = hashed.split("$")
        check_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(check_key.hex(), key_hex)
    except Exception:
        return False


def chunk_text(text: str, max_chars: int = 650, overlap: int = 80) -> List[Tuple[str, str]]:
    """Split text into semantic chunks with headings and overlaps."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return [("Notice", text)]

    current_heading = lines[0] if len(lines[0]) < 80 else "General Notice"
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
            # Keep overlap
            overlap_words = chunk_body.split()[-12:]
            current_buf = [" ".join(overlap_words)]
            current_len = len(current_buf[0])

    if current_buf:
        chunk_body = " ".join(current_buf)
        if not chunks or chunk_body != chunks[-1][1]:
            chunks.append((current_heading, chunk_body))

    return chunks


def seed_database(force: bool = False) -> None:
    """Seed campus demo data into SQLite database."""
    today = date.today()

    def d_offset(days: int) -> str:
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    with get_connection() as conn:
        cursor = conn.cursor()

        # Check if already seeded
        existing_users = cursor.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        if existing_users > 0 and not force:
            return

        if force:
            cursor.execute("DELETE FROM notifications;")
            cursor.execute("DELETE FROM reminders;")
            cursor.execute("DELETE FROM deadlines;")
            cursor.execute("DELETE FROM deadline_done;")
            cursor.execute("DELETE FROM form_submissions;")
            cursor.execute("DELETE FROM forms;")
            cursor.execute("DELETE FROM questions;")
            cursor.execute("DELETE FROM chats;")
            cursor.execute("DELETE FROM chunks;")
            cursor.execute("DELETE FROM chunks_fts;")
            cursor.execute("DELETE FROM documents;")
            cursor.execute("DELETE FROM offices;")
            cursor.execute("DELETE FROM student_profiles;")
            cursor.execute("DELETE FROM users;")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Seed Demo Users
        users_data = [
            ("admin1", hash_password("admin123"), "admin", "Admin Office Staff", "admin@example.edu"),
            ("student1", hash_password("student123"), "student", "Aarav Sharma", "aarav@example.edu"),
            ("student2", hash_password("student123"), "student", "Priya Patel", "priya@example.edu"),
        ]
        cursor.executemany("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (?, ?, ?, ?, ?)
        """, users_data)

        admin_id = cursor.execute("SELECT id FROM users WHERE username = 'admin1'").fetchone()[0]
        student1_id = cursor.execute("SELECT id FROM users WHERE username = 'student1'").fetchone()[0]
        student2_id = cursor.execute("SELECT id FROM users WHERE username = 'student2'").fetchone()[0]

        # 2. Seed Student Profiles
        # student1 has fully filled profile
        cursor.execute("""
            INSERT INTO student_profiles (
                user_id, roll_no, enrollment_no, programme, department, semester,
                section, email, phone, hostel_block, room_no, guardian_name, guardian_phone
            ) VALUES (?, '22CS045', 'EN2022CS0045', 'B.Tech Computer Science', 'Computer Science & Engineering',
                      '6', 'A', 'aarav@example.edu', '+91-98765-43210', 'Block C', '304',
                      'Rajesh Sharma', '+91-98765-43219')
        """, (student1_id,))

        # student2 has partially filled profile (missing hostel & guardian to test autofill highlights)
        cursor.execute("""
            INSERT INTO student_profiles (
                user_id, roll_no, enrollment_no, programme, department, semester,
                section, email, phone, hostel_block, room_no, guardian_name, guardian_phone
            ) VALUES (?, '23EC012', 'EN2023EC0012', 'B.Tech Electronics', 'Electronics & Communication',
                      '4', 'B', 'priya@example.edu', '+91-98111-22233', NULL, NULL, NULL, NULL)
        """, (student2_id,))

        # 3. Seed Campus Offices
        offices_data = [
            ("Admissions Office", "Administrative Block, Room 102", "+91-11-2345-6701",
             "admissions@example.edu", "Mon-Fri: 9:00 AM - 5:00 PM",
             "admission, enrollment, bonafide, certificate, id card, transfer, migration"),
            ("Accounts & Fee Office", "Administrative Block, Ground Floor, Counter 3", "+91-11-2345-6702",
             "accounts@example.edu", "Mon-Fri: 9:30 AM - 4:00 PM",
             "fee, fees, payment, fine, waiver, refund, challan, receipt, accounts, jama"),
            ("Hostel Office", "Central Student Center, 1st Floor", "+91-11-2345-6703",
             "hostel@example.edu", "Mon-Sat: 8:00 AM - 8:00 PM",
             "hostel, room, warden, curfew, mess, accommodation, block, room change"),
            ("Examination Cell", "Academic Complex, Block A, Room 204", "+91-11-2345-6704",
             "exams@example.edu", "Mon-Fri: 9:00 AM - 5:30 PM",
             "exam, examination, mid-term, final, timetable, schedule, admit card, grade, marksheet, re-eval"),
            ("Student Affairs Office", "Student Activity Center, Room G-05", "+91-11-2345-6705",
             "studentaffairs@example.edu", "Mon-Fri: 9:00 AM - 6:00 PM",
             "events, clubs, fest, volunteer, cultural, sports, student council, activities"),
        ]
        cursor.executemany("""
            INSERT INTO offices (name, location, phone, email, hours, keywords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, offices_data)

        admissions_off_id = cursor.execute("SELECT id FROM offices WHERE name = 'Admissions Office'").fetchone()[0]
        accounts_off_id = cursor.execute("SELECT id FROM offices WHERE name = 'Accounts & Fee Office'").fetchone()[0]
        hostel_off_id = cursor.execute("SELECT id FROM offices WHERE name = 'Hostel Office'").fetchone()[0]
        exam_off_id = cursor.execute("SELECT id FROM offices WHERE name = 'Examination Cell'").fetchone()[0]
        affairs_off_id = cursor.execute("SELECT id FROM offices WHERE name = 'Student Affairs Office'").fetchone()[0]

        # 4. Seed Forms
        forms_data = [
            (
                "hostel-room-request",
                "Hostel Room Request",
                "Apply for hostel room accommodation or request a room change across campus blocks.",
                hostel_off_id,
                "Please verify your contact details. Choose your preferred hostel block and state your reason clearly.",
                json.dumps([
                    {"name": "full_name", "label": "Student Full Name", "type": "text", "required": True, "profile_key": "full_name"},
                    {"name": "roll_no", "label": "Roll Number", "type": "text", "required": True, "profile_key": "roll_no"},
                    {"name": "programme", "label": "Programme / Branch", "type": "text", "required": True, "profile_key": "programme"},
                    {"name": "semester", "label": "Current Semester", "type": "text", "required": True, "profile_key": "semester"},
                    {"name": "hostel_block", "label": "Current Hostel Block", "type": "text", "required": False, "profile_key": "hostel_block"},
                    {"name": "preferred_block", "label": "Preferred Hostel Block", "type": "select", "required": True,
                     "options": ["Block A (Boys)", "Block B (Boys)", "Block C (Girls)", "Block D (Girls)"]},
                    {"name": "reason", "label": "Reason for Room Request / Change", "type": "textarea", "required": True},
                    {"name": "guardian_phone", "label": "Guardian Contact Number", "type": "text", "required": True, "profile_key": "guardian_phone"},
                ])
            ),
            (
                "bonafide-certificate-request",
                "Bonafide Certificate Request",
                "Request an official bonafide study certificate for bus pass, educational loan, or visa verification.",
                admissions_off_id,
                "Standard certificate issuance takes 2 working days. A fee of Rs 50 is payable at Counter 3.",
                json.dumps([
                    {"name": "full_name", "label": "Student Full Name", "type": "text", "required": True, "profile_key": "full_name"},
                    {"name": "roll_no", "label": "Roll Number", "type": "text", "required": True, "profile_key": "roll_no"},
                    {"name": "programme", "label": "Programme / Branch", "type": "text", "required": True, "profile_key": "programme"},
                    {"name": "semester", "label": "Current Semester", "type": "text", "required": True, "profile_key": "semester"},
                    {"name": "purpose", "label": "Purpose of Certificate", "type": "select", "required": True,
                     "options": ["Bus / Metro Concession Pass", "Bank Education Loan", "Passport / Visa Application", "Internship Verification", "Other Official Purpose"]},
                    {"name": "copies", "label": "Number of Copies Required", "type": "number", "required": True},
                ])
            ),
            (
                "mid-term-late-admission-request",
                "Mid-Term Late Admission Request",
                "Special registration form for students admitted after semester commencement to appear in mid-term exams.",
                exam_off_id,
                "Submit before the registration deadline to receive your room allocation and admit card.",
                json.dumps([
                    {"name": "full_name", "label": "Student Full Name", "type": "text", "required": True, "profile_key": "full_name"},
                    {"name": "roll_no", "label": "Roll Number", "type": "text", "required": True, "profile_key": "roll_no"},
                    {"name": "programme", "label": "Programme / Degree", "type": "text", "required": True, "profile_key": "programme"},
                    {"name": "semester", "label": "Current Semester", "type": "text", "required": True, "profile_key": "semester"},
                    {"name": "subjects", "label": "Course Codes & Subject Names", "type": "textarea", "required": True},
                    {"name": "reason", "label": "Reason for Late Admission Appearance", "type": "textarea", "required": True},
                ])
            ),
            (
                "fee-late-payment-waiver-request",
                "Fee Late-Payment Waiver Request",
                "Request late fee waiver or installment extension for semester tuition fees.",
                accounts_off_id,
                "Late payment fine of Rs 100 per day applies unless an official waiver is approved by the Accounts Office.",
                json.dumps([
                    {"name": "full_name", "label": "Student Full Name", "type": "text", "required": True, "profile_key": "full_name"},
                    {"name": "roll_no", "label": "Roll Number", "type": "text", "required": True, "profile_key": "roll_no"},
                    {"name": "programme", "label": "Programme / Branch", "type": "text", "required": True, "profile_key": "programme"},
                    {"name": "semester", "label": "Current Semester", "type": "text", "required": True, "profile_key": "semester"},
                    {"name": "amount", "label": "Outstanding Tuition Fee Amount (INR)", "type": "text", "required": True},
                    {"name": "reason", "label": "Reason for Fee Payment Delay", "type": "textarea", "required": True},
                    {"name": "supporting_note", "label": "Reference / Supporting Note", "type": "text", "required": False},
                ])
            ),
        ]

        cursor.executemany("""
            INSERT INTO forms (slug, title, description, office_id, instructions, fields_json, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, forms_data)

        form_hostel_id = cursor.execute("SELECT id FROM forms WHERE slug = 'hostel-room-request'").fetchone()[0]
        form_bonafide_id = cursor.execute("SELECT id FROM forms WHERE slug = 'bonafide-certificate-request'").fetchone()[0]
        form_midterm_id = cursor.execute("SELECT id FROM forms WHERE slug = 'mid-term-late-admission-request'").fetchone()[0]
        form_fee_id = cursor.execute("SELECT id FROM forms WHERE slug = 'fee-late-payment-waiver-request'").fetchone()[0]

        # 5. Seed Documents
        # 14 documents from Section 10
        docs_to_insert = [
            # 1. PPT Submission Last Date
            {
                "title": "PPT Submission Last Date",
                "doc_type": "notice",
                "category": "Academic",
                "office_id": None,
                "department": "Academic Affairs",
                "publish_date": d_offset(-3),
                "expiry_date": d_offset(30),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "OFFICIAL NOTICE: Final Semester Project PPT Submission Deadline.\n\n"
                    "All final year undergraduate and postgraduate students must submit their project presentation slides (PPT) "
                    f"by {d_offset(2)} at 5:00 PM. Submissions must be uploaded via the campus academic portal or delivered on a USB drive "
                    "to the Department Project Coordinator. Late submissions will attract a 10% grade penalty. "
                    "Ensure your title slide includes project title, group member names, roll numbers, and guide name. "
                    "For clarifications, contact the Academic Affairs Office or your respective project guides."
                ),
                "summary": f"Final project presentation slides must be submitted by {d_offset(2)} at 5:00 PM.",
                "deadline": ("PPT Submission Deadline", d_offset(2), "17:00"),
                "related_form_id": None,
            },
            # 2. Semester Fee Payment Last Date
            {
                "title": "Semester Fee Payment Last Date",
                "doc_type": "notice",
                "category": "Fees",
                "office_id": accounts_off_id,
                "department": "Accounts & Fee Office",
                "publish_date": d_offset(-5),
                "expiry_date": d_offset(45),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "NOTICE: Semester Tuition Fee Payment Schedule.\n\n"
                    f"The last date for semester tuition fee payment without penalty is {d_offset(9)}. "
                    "Students may pay online via the student fee payment gateway or at Accounts Counter 3 in the Administrative Block. "
                    "A late fine of Rs 100 per day will be levied automatically on all payments made after the last date. "
                    "Students facing genuine financial distress may submit a Fee Late-Payment Waiver Request before the due date. "
                    "Contact the Accounts & Fee Office at accounts@example.edu or +91-11-2345-6702 for challan verifications."
                ),
                "summary": f"Semester tuition fee last date is {d_offset(9)}. Late fine of Rs 100 per day applies afterwards.",
                "deadline": ("Semester Fee Payment Due Date", d_offset(9), "23:59"),
                "related_form_id": form_fee_id,
            },
            # 3. Mid-Term Exam: Late Admitted Students
            {
                "title": "Mid-Term Exam: Late Admitted Students",
                "doc_type": "notice",
                "category": "Exam",
                "office_id": exam_off_id,
                "department": "Examination Cell",
                "publish_date": d_offset(-2),
                "expiry_date": d_offset(25),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "EXAMINATION CELL CIRCULAR: Mid-Term Examination for Late Admitted Students.\n\n"
                    "Students enrolled under late admission rounds are hereby notified that the special mid-term examinations "
                    f"will be conducted on {d_offset(10)} and {d_offset(11)} across designated lecture halls. "
                    f"Mandatory online form registration closes on {d_offset(1)} at 11:59 PM. "
                    "Students must fill out the Mid-Term Late Admission Request form to be assigned an exam room and admit card. "
                    "Room allocations and detailed timetables will be published on the notice board on the morning of the exam. "
                    "For questions, reach the Examination Cell at Academic Complex Room 204 or exams@example.edu."
                ),
                "summary": f"Registration closes on {d_offset(1)}. Mid-term exams take place on {d_offset(10)} and {d_offset(11)}.",
                "deadline": ("Late Admission Exam Registration Deadline", d_offset(1), "23:59"),
                "related_form_id": form_midterm_id,
            },
            # 4. Saturday Observed as Normal Teaching Day
            {
                "title": "Saturday Observed as Normal Teaching Day",
                "doc_type": "circular",
                "category": "Academic",
                "office_id": None,
                "department": "Academic Affairs",
                "publish_date": d_offset(-1),
                "expiry_date": d_offset(14),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CIRCULAR: Teaching Schedule Announcement.\n\n"
                    "This is to inform all faculty members and students that the upcoming Saturday is observed as a normal teaching day "
                    "to compensate for instructional days lost during the annual festival. "
                    "All classes and laboratory sessions will strictly follow the Wednesday academic timetable. "
                    "Attendance will be recorded and calculated towards overall semester minimum requirements. "
                    "Campus transport buses will operate following normal weekday bus routes and timings."
                ),
                "summary": "Upcoming Saturday will be observed as a normal teaching day following Wednesday timetable.",
                "deadline": None,
                "related_form_id": None,
            },
            # 5. Library Book Return Drive (EXPIRED notice for OLD badge demo)
            {
                "title": "Library Book Return Drive",
                "doc_type": "notice",
                "category": "General",
                "office_id": None,
                "department": "Central Library",
                "publish_date": d_offset(-20),
                "expiry_date": d_offset(-5),  # Expired 5 days ago!
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "LIBRARY NOTICE: Annual Book Return and Fine Amnesty Drive.\n\n"
                    f"The Central Library annual book return drive concluded on {d_offset(-5)}. "
                    "Students who borrowed books during the semester were permitted to return books with waiver of overdue fines. "
                    "Since the drive is now closed, standard library overdue fines of Rs 5 per day per book apply. "
                    "Library clearance certificates will only be issued after all outstanding books and fines are settled."
                ),
                "summary": f"The library book return drive ended on {d_offset(-5)}.",
                "deadline": None,
                "related_form_id": None,
            },
            # 6. Student Handbook: Attendance & Conduct
            {
                "title": "Student Handbook: Attendance & Conduct",
                "doc_type": "handbook",
                "category": "Academic",
                "office_id": None,
                "department": "Academic Affairs",
                "publish_date": d_offset(-30),
                "expiry_date": None,
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CAMPUS STUDENT HANDBOOK: Academic Regulations & Conduct Code.\n\n"
                    "1. Attendance Requirement: Students must maintain a minimum attendance of 75% in each registered course "
                    "to be eligible to appear for the end-semester final examinations. Students falling between 65% and 75% due to medical reasons "
                    "must submit medical certificates within 3 working days of returning to campus.\n\n"
                    "2. Leave Procedure: Medical leave applications must be endorsed by the campus health center medical officer "
                    "and submitted to the department dean.\n\n"
                    "3. Campus Conduct: Ragging, substance use, and vandalism are strictly prohibited with zero tolerance under university bylaws."
                ),
                "summary": "Mandatory minimum 75% attendance required for examinations; medical leave rules and student conduct code.",
                "deadline": None,
                "related_form_id": None,
            },
            # 7. Fee Rules
            {
                "title": "Fee Rules & Regulations",
                "doc_type": "rules",
                "category": "Fees",
                "office_id": accounts_off_id,
                "department": "Accounts & Fee Office",
                "publish_date": d_offset(-30),
                "expiry_date": None,
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "OFFICIAL UNIVERSITY FEE RULES:\n\n"
                    "1. Payment Installments: Academic tuition fees may be paid in up to two equal installments upon prior written approval "
                    "from the Accounts Office. The first installment is due at semester registration.\n\n"
                    "2. Late Fine Policy: A late fine of Rs 100 per day is charged for delays beyond the published deadline up to a maximum of Rs 3,000.\n\n"
                    "3. Academic Refund Policy: Tuition fee refund on withdrawal is 100% up to 15 days before semester commencement, "
                    "80% within the first 15 days, and 0% thereafter. Note that hostel fees are governed by independent residential policies and "
                    "tuition refund rules do not apply to hostel fees."
                ),
                "summary": "Rules governing tuition fee installments, late fine rate of Rs 100 per day, and tuition withdrawal refund structure.",
                "deadline": None,
                "related_form_id": form_fee_id,
            },
            # 8. Hostel Rules
            {
                "title": "Hostel Residence Rules & Regulations",
                "doc_type": "rules",
                "category": "Hostel",
                "office_id": hostel_off_id,
                "department": "Hostel Office",
                "publish_date": d_offset(-30),
                "expiry_date": None,
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CAMPUS HOSTEL RULES AND REGULATIONS:\n\n"
                    "1. Curfew & Gate Timings: The mandatory hostel curfew time is 10:00 PM every night. "
                    "Students must scan their biometric student ID card at the hostel turnstiles prior to 10:00 PM. "
                    "Late entry requires written permission from the Chief Warden.\n\n"
                    "2. Visitors Policy: Outside guests and day scholars are permitted only in the ground-floor visitor lounge until 7:00 PM. "
                    "No unauthorized visitors are permitted in residential corridors or rooms.\n\n"
                    "3. Room Change: Room change requests may be submitted only at the beginning of each semester using the official Hostel Room Request form. "
                    "Mutual room swapping without warden approval is strictly prohibited."
                ),
                "summary": "Mandatory curfew at 10:00 PM; visitor restrictions; room change procedures via hostel office.",
                "deadline": None,
                "related_form_id": form_hostel_id,
            },
            # 9. How to get a Bonafide Certificate
            {
                "title": "Process Guide: How to get a Bonafide Certificate",
                "doc_type": "process_guide",
                "category": "Admission",
                "office_id": admissions_off_id,
                "department": "Admissions Office",
                "publish_date": d_offset(-15),
                "expiry_date": None,
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "STUDENT PROCESS GUIDE: Obtaining an Official Bonafide Study Certificate.\n\n"
                    "Step 1: Fill out the online Bonafide Certificate Request form on the CampusFlow portal.\n"
                    "Step 2: Pay the nominal certificate processing fee of Rs 50 at Counter 3 in the Administrative Block.\n"
                    "Step 3: What documents are needed for bonafide: Bring your original Student ID Card and current semester fee receipt.\n"
                    "Step 4: Standard processing time is 2 working days. Collect your signed and stamped certificate from the Admissions Office (Room 102). "
                    "Certificates can be utilized for bus pass, educational loan, or passport verification."
                ),
                "summary": "Steps to get bonafide certificate: submit online form, pay Rs 50 fee, 2 working days processing time.",
                "deadline": None,
                "related_form_id": form_bonafide_id,
            },
            # 10. Hostel Room Request: Steps
            {
                "title": "Process Guide: Hostel Room Request Steps",
                "doc_type": "process_guide",
                "category": "Hostel",
                "office_id": hostel_off_id,
                "department": "Hostel Office",
                "publish_date": d_offset(-15),
                "expiry_date": None,
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "PROCESS GUIDE: How to Apply for a Hostel Room or Room Change.\n\n"
                    "Step 1: Check available vacancies on the hostel notice board.\n"
                    "Step 2: Submit the online Hostel Room Request form with your preferred block and rationale.\n"
                    "Step 3: The Hostel Office verifies student conduct and disciplinary record with the warden.\n"
                    "Step 4: Room allotment notifications are issued within 3 working days via email and SMS. "
                    "Collect room keys from the caretaker after signing the inventory checklist."
                ),
                "summary": "Guide for hostel room application and room change requests with 3-day turnaround.",
                "deadline": None,
                "related_form_id": form_hostel_id,
            },
            # 11. Robotics Club Workshop: Arduino Basics
            {
                "title": "Robotics Club Workshop: Arduino Basics",
                "doc_type": "event",
                "category": "Events",
                "office_id": affairs_off_id,
                "department": "Robotics Club",
                "publish_date": d_offset(-2),
                "expiry_date": d_offset(6),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CAMPUS EVENT: Robotics Club Workshop on Arduino & Sensor Interfacing.\n\n"
                    f"Join the campus Robotics Club for an intensive beginner-friendly workshop on Arduino microcontroller programming and hardware sensors. "
                    f"Date & Time: {d_offset(5)} at 3:00 PM. "
                    "Venue: Lab 3, Block B. "
                    "All participants will receive breadboards, microcontrollers, and electronic components for hands-on exercises. "
                    "Seats are limited to 40 students. Register online at https://example.edu/events/robotics-workshop before seats fill up. "
                    "Contact the student affairs coordinator for venue directions or kit inquiries."
                ),
                "summary": f"Arduino robotics workshop on {d_offset(5)} at 3:00 PM in Lab 3, Block B.",
                "deadline": None,
                "related_form_id": None,
                "event_start": f"{d_offset(5)} 15:00:00",
                "venue": "Lab 3, Block B",
                "registration_url": "https://example.edu/events/robotics-workshop",
            },
            # 12. Hackathon Info Session
            {
                "title": "Hackathon Info Session",
                "doc_type": "event",
                "category": "Events",
                "office_id": affairs_off_id,
                "department": "Innovation & Coding Club",
                "publish_date": d_offset(-2),
                "expiry_date": d_offset(5),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CAMPUS EVENT: Aarambhathon Hackathon Orientation & Problem Briefing.\n\n"
                    f"Orientation briefing for teams participating in the upcoming 36-hour campus hackathon. "
                    f"Date: {d_offset(4)} at 4:00 PM. "
                    "Venue: Seminar Hall (Central Auditorium Building). "
                    "Judges will explain problem statements, evaluation rubrics, cloud credit allocations, and hardware safety guidelines. "
                    "Team leaders must confirm team attendance via registration link: https://example.edu/events/hackathon-info."
                ),
                "summary": f"Hackathon orientation session on {d_offset(4)} at Seminar Hall.",
                "deadline": None,
                "related_form_id": None,
                "event_start": f"{d_offset(4)} 16:00:00",
                "venue": "Seminar Hall",
                "registration_url": "https://example.edu/events/hackathon-info",
            },
            # 13. Cultural Fest Volunteer Registration
            {
                "title": "Cultural Fest Volunteer Registration",
                "doc_type": "event",
                "category": "Events",
                "office_id": affairs_off_id,
                "department": "Student Affairs Office",
                "publish_date": d_offset(-1),
                "expiry_date": d_offset(8),
                "status": "published",
                "source_type": "typed",
                "raw_text": (
                    "CALL FOR VOLUNTEERS: Annual Campus Cultural Fest.\n\n"
                    "Students wishing to volunteer for logistics, stage management, hospitality, and media coverage during the cultural festival "
                    f"must attend the briefing and registration drive on {d_offset(7)} at 10:00 AM at the Student Affairs Office (SAC Room G-05). "
                    "Volunteers will receive official duty certificates and event merchandise. "
                    "Online registration link: https://example.edu/events/fest-volunteer."
                ),
                "summary": f"Volunteer registration on {d_offset(7)} at Student Affairs Office.",
                "deadline": None,
                "related_form_id": None,
                "event_start": f"{d_offset(7)} 10:00:00",
                "venue": "Student Affairs Office",
                "registration_url": "https://example.edu/events/fest-volunteer",
            },
            # 14. DRAFT - Project Review Schedule (with deliberate conflicts to demonstrate AI validation)
            {
                "title": "Project Review Schedule",
                "doc_type": "notice",
                "category": "Academic",
                "office_id": None,
                "department": "Academic Affairs",
                "publish_date": d_offset(0),
                "expiry_date": d_offset(30),
                "status": "draft",  # DRAFT: HIDDEN FROM STUDENTS
                "source_type": "typed",
                "raw_text": (
                    "DRAFT DOCUMENT: Project Review Schedule Announcement.\n\n"
                    f"All undergraduate teams must complete their preliminary code submission by {d_offset(6)}. "
                    f"However, the final evaluation submission deadline is set for {d_offset(8)}. "
                    "Mid-semester project reviews will take place next Friday in the project lab. "
                    "Please ensure guides have signed your progress report."
                ),
                "summary": "Draft notice with conflicting dates designed to demonstrate AI validation flags.",
                "deadline": None,
                "related_form_id": None,
                "ai_flags": json.dumps([
                    {"severity": "blocking", "message": f"Conflicting submission dates detected ({d_offset(6)} vs {d_offset(8)})", "field": "deadlines"},
                    {"severity": "warning", "message": "Relative date 'next Friday' found. Please specify exact calendar date.", "field": "text"}
                ]),
            },
        ]

        # Insert documents, chunks, FTS rows, and deadlines
        for doc in docs_to_insert:
            event_start = doc.get("event_start")
            venue = doc.get("venue")
            reg_url = doc.get("registration_url")
            flags_json = doc.get("ai_flags")

            cursor.execute("""
                INSERT INTO documents (
                    title, doc_type, category, office_id, department, publish_date, expiry_date,
                    status, is_sample, source_type, raw_text, summary, event_start, venue,
                    registration_url, related_form_id, ai_flags, created_by, created_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc["title"], doc["doc_type"], doc["category"], doc["office_id"],
                doc["department"], doc["publish_date"], doc["expiry_date"], doc["status"],
                doc["source_type"], doc["raw_text"], doc["summary"], event_start, venue,
                reg_url, doc["related_form_id"], flags_json, admin_id, now_str,
                now_str if doc["status"] == "published" else None
            ))

            doc_id = cursor.lastrowid

            # Chunk document and index in FTS if published
            chunks = chunk_text(doc["raw_text"])
            chunk_ids = []
            for idx, (heading, text_part) in enumerate(chunks):
                cursor.execute("""
                    INSERT INTO chunks (document_id, chunk_index, heading, text)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, idx, heading, text_part))
                chunk_ids.append(cursor.lastrowid)

            if doc["status"] == "published":
                # Add to FTS
                for idx, (heading, text_part) in enumerate(chunks):
                    cursor.execute("""
                        INSERT INTO chunks_fts (title, heading, text, chunk_id, document_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (doc["title"], heading, text_part, str(chunk_ids[idx]), str(doc_id)))

                # Add deadline and reminders if configured
                dl_info = doc.get("deadline")
                if dl_info:
                    label, due_date, due_time = dl_info
                    cursor.execute("""
                        INSERT INTO deadlines (document_id, label, due_date, due_time, status)
                        VALUES (?, ?, ?, ?, 'confirmed')
                    """, (doc_id, label, due_date, due_time))
                    deadline_id = cursor.lastrowid

                    # Schedule 2d and 1d reminders
                    due_dt = datetime.strptime(due_date, "%Y-%m-%d")
                    remind_2d = (due_dt - timedelta(days=2)).strftime("%Y-%m-%d 09:00:00")
                    remind_1d = (due_dt - timedelta(days=1)).strftime("%Y-%m-%d 09:00:00")

                    cursor.execute("""
                        INSERT INTO reminders (deadline_id, remind_at, kind)
                        VALUES (?, ?, '2d'), (?, ?, '1d')
                    """, (deadline_id, remind_2d, deadline_id, remind_1d))

        conn.commit()


if __name__ == "__main__":
    from backend.database import init_db
    init_db()
    seed_database(force=True)
    print("Database initialized and sample data seeded successfully.")
