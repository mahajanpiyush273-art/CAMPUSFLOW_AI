"""
CampusFlow AI - Automated Test Suite
Executes all 28 evaluation questions against the Ask engine,
verifies grounded confidence scoring, citations, and fallback safety,
prints a formatted ASCII summary table, and exports tests/results.csv.
"""

import csv
from datetime import datetime
import os
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.answer import answer_student_question
from backend.database import get_connection, init_db
from backend.seed import seed_database


def run_all_tests():
    print("=" * 80)
    print("  CAMPUSFLOW AI - AUTOMATED ACCURACY & SAFETY TEST SUITE")
    print("  Evaluating all 28 benchmark questions from Section 11")
    print("=" * 80)

    # 1. Initialize and seed DB if needed
    init_db()
    seed_database(force=False)

    # 2. Get student user id
    with get_connection() as conn:
        cursor = conn.cursor()
        student_row = cursor.execute("SELECT id FROM users WHERE username = 'student1'").fetchone()
        if not student_row:
            print("ERROR: student1 user not found in database.")
            sys.exit(1)
        student_id = student_row[0]

    # 3. Read test questions CSV
    csv_path = Path(__file__).resolve().parent.parent / "tests" / "test_questions.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.")
        sys.exit(1)

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        test_cases = list(reader)

    print(f"Loaded {len(test_cases)} test cases from {csv_path.name}\n")

    results = []
    passed_count = 0
    failed_count = 0

    # Cache for follow-up turns
    chat_history = []

    print(f"{'#':<3} | {'Question':<34} | {'Status':<12} | {'Conf':<6} | {'Result':<6} | {'Notes / Match'}")
    print("-" * 88)

    for tc in test_cases:
        t_id = int(tc["id"])
        question = tc["question"]
        expected_status = tc["expected_status"]
        expected_kw = tc["expected_notice_keyword"]
        min_conf = int(tc["min_confidence"])
        max_conf = int(tc["max_confidence"])
        must_contain = tc.get("must_contain", "").strip()
        must_not_contain = tc.get("must_not_contain", "").strip()
        category = tc.get("category", "")

        # Prepare context for follow-up turns (questions 20 and 21)
        history_for_turn = None
        if t_id == 20:
            history_for_turn = [
                {"role": "student", "content": "fees payment ki last date kya hai"},
                {"role": "assistant", "content": "The last date for semester tuition fee payment is upcoming."}
            ]
        elif t_id == 21:
            history_for_turn = [
                {"role": "student", "content": "how to apply for hostel room change?"},
                {"role": "assistant", "content": "You can apply using the online Hostel Room Request form."}
            ]

        start_t = time.time()
        resp = answer_student_question(
            question=question,
            user_id=student_id,
            recent_history=history_for_turn
        )
        elapsed = time.time() - start_t

        status = resp.get("status")
        confidence = resp.get("confidence", 0)
        answer = resp.get("answer", "")
        source = resp.get("source") or {}
        source_title = source.get("title", "")
        source_snippet = source.get("snippet", "")
        source_full = source.get("full_text", "")
        matched_sentence = resp.get("matched_sentence", "")

        # Evaluation checks
        failures = []

        # 1. Status Check
        if expected_status == "answered" and status != "answered":
            failures.append(f"Expected status 'answered', got '{status}'")
        elif expected_status == "not_verified" and status != "not_verified":
            failures.append(f"Expected status 'not_verified', got '{status}'")

        # 2. Confidence Range Check
        if not (min_conf <= confidence <= max_conf):
            failures.append(f"Confidence {confidence}% out of range [{min_conf}%, {max_conf}%]")

        # 3. Source Citation Keyword Check (if verified)
        if expected_status == "answered" and expected_kw != "none":
            kw_match = (
                expected_kw.lower() in source_title.lower() or
                expected_kw.lower() in answer.lower()
            )
            if not kw_match:
                failures.append(f"Expected citation keyword '{expected_kw}', got '{source_title}'")

        # 4. Must Contain Check
        if must_contain:
            search_pool = f"{answer} {source_snippet} {matched_sentence} {source_title} {source_full}".lower()
            if must_contain.lower() not in search_pool:
                failures.append(f"Missing required phrase: '{must_contain}'")

        # 5. Must Not Contain Check
        if must_not_contain:
            if must_not_contain.lower() in answer.lower():
                failures.append(f"Forbidden phrase found in answer: '{must_not_contain}'")

        # Determine outcome
        passed = len(failures) == 0
        if passed:
            passed_count += 1
            res_str = "PASS"
            note_str = source_title[:28] if source_title else (resp.get("office", {}).get("name") or "Safe Refusal")
        else:
            failed_count += 1
            res_str = "FAIL"
            note_str = "; ".join(failures)[:30]

        q_disp = question[:32] + ("..." if len(question) > 32 else "")
        print(f"{t_id:<3} | {q_disp:<34} | {status:<12} | {confidence:>3}%  | {res_str:<6} | {note_str}")

        results.append({
            "id": t_id,
            "question": question,
            "expected_status": expected_status,
            "actual_status": status,
            "confidence": confidence,
            "result": res_str,
            "citation": source_title,
            "failures": " | ".join(failures),
            "elapsed_seconds": round(elapsed, 2)
        })

    print("-" * 88)
    pct = int(round((passed_count / len(test_cases)) * 100))
    print(f"TEST RESULTS: {passed_count}/{len(test_cases)} PASSED ({pct}% Success Rate)\n")

    # Export results to CSV
    results_path = Path(__file__).resolve().parent.parent / "tests" / "results.csv"
    with open(results_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "question", "expected_status", "actual_status", "confidence", "result", "citation", "failures", "elapsed_seconds"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Detailed execution log saved to: {results_path}")

    if failed_count > 0:
        print(f"\n[WARNING] {failed_count} test(s) failed. Check details in tests/results.csv.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] ALL 28 TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    run_all_tests()
