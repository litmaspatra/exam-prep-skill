#!/usr/bin/env python3
"""
MCQ Drill & Mock Exam Engine (OMR-style exams such as IGNOU CLIS TEE).

Modes:
  Drill   : python scripts/mcq_quiz.py --course BLII-012 --count 15
            Immediate feedback + explanation after each question.
  Mock    : python scripts/mcq_quiz.py --course BLII-012 --mock
            Exam simulation (default 50 questions), no feedback until the end.
  Mixed   : python scripts/mcq_quiz.py --all --count 20
  Report  : python scripts/mcq_quiz.py --report     (history from progress.json)
  Selftest: python scripts/mcq_quiz.py --selftest   (validate bank, no input)

Every attempt is appended to progress.json (repo root) unless --no-save.
The bank (data/clis_mcq_bank.json) is seeded with high-yield questions; grow
it by adding questions extracted from the real PYQs you download with
scripts/fetch_materials.py.
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANK = REPO_ROOT / "data" / "clis_mcq_bank.json"
PROGRESS_FILE = REPO_ROOT / "progress.json"
LETTERS = "ABCD"


def load_bank(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Could not read question bank {path}: {e}")
    questions = data.get("questions", [])
    errors = []
    seen = set()
    for i, q in enumerate(questions):
        for field in ("id", "course", "question", "options", "answer_index"):
            if field not in q:
                errors.append(f"Q#{i}: missing '{field}'")
        qid = q.get("id")
        if qid in seen:
            errors.append(f"duplicate id: {qid}")
        seen.add(qid)
        if not isinstance(q.get("options"), list) or len(q.get("options", [])) != 4:
            errors.append(f"{qid}: needs exactly 4 options")
        if not isinstance(q.get("answer_index"), int) or not 0 <= q.get("answer_index", -1) < 4:
            errors.append(f"{qid}: answer_index must be 0-3")
    if not questions:
        errors.append("bank is empty")
    return questions, errors


def save_progress(entry):
    history = []
    if PROGRESS_FILE.exists():
        try:
            history = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(entry)
    PROGRESS_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def show_report():
    if not PROGRESS_FILE.exists():
        print("No progress yet. Run a drill: python scripts/mcq_quiz.py --course BLII-012 --count 10")
        return
    history = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    print(f"Progress so far ({len(history)} attempts):\n")
    by_course = {}
    for h in history:
        by_course.setdefault(h.get("course", "?"), []).append(h)
    print("| Course | Attempts | Best | Last | Last Date |")
    print("| :--- | :---: | :---: | :---: | :--- |")
    for course, attempts in sorted(by_course.items()):
        best = max(a["pct"] for a in attempts)
        last = attempts[-1]
        print(f"| {course} | {len(attempts)} | {best:.0f}% | {last['pct']:.0f}% ({last['correct']}/{last['total']}) | {last['ts'][:10]} |")
    print()


def ask_choice():
    while True:
        try:
            raw = input("Your answer (A-D, or Q to quit): ").strip().lower()
        except EOFError:
            return None
        if raw in ("q", "quit"):
            return None
        if raw in ("a", "b", "c", "d"):
            return LETTERS.index(raw.upper())
        if raw in ("1", "2", "3", "4"):
            return int(raw) - 1
        print("  Please answer A, B, C or D.")


def run_quiz(questions, course_label, mode, mock, no_save):
    print(f"\n=== {mode} — {course_label} — {len(questions)} questions ===")
    if mock:
        print("Exam simulation: no feedback until the end. Target pace: ~1 minute/question.\n")
    start = time.time()
    correct = 0
    results = []
    for n, q in enumerate(questions, 1):
        order = list(range(4))
        random.shuffle(order)  # shuffle option positions each run
        print(f"Q{n}. [{q['course']}] {q['question']}")
        for i, oi in enumerate(order):
            print(f"   {LETTERS[i]}) {q['options'][oi]}")
        picked = ask_choice()
        if picked is None:
            print("(ending early)")
            break
        is_right = order[picked] == q["answer_index"]
        correct += is_right
        results.append({"id": q["id"], "course": q["course"], "correct": bool(is_right)})
        if not mock:
            mark = "Correct!" if is_right else f"Wrong — answer is {LETTERS[order.index(q['answer_index'])]})"
            print(f"  {mark}")
            if q.get("explanation"):
                print(f"  {q['explanation']}")
            print()

    total = len(results)
    elapsed = time.time() - start
    pct = (100.0 * correct / total) if total else 0.0
    print("\n----------------------------------------")
    print(f"Score: {correct}/{total} = {pct:.0f}%   (time: {int(elapsed // 60)}m {int(elapsed % 60)}s)")
    by_block = {}
    for r in results:
        by_block.setdefault(r["course"], [0, 0])
        by_block[r["course"]][1] += 1
        by_block[r["course"]][0] += r["correct"]
    for course, (c, t) in sorted(by_block.items()):
        print(f"  {course}: {c}/{t}")
    print("----------------------------------------")

    if mock and results:
        wrong = [r for r in results if not r["correct"]]
        if wrong:
            print("Review the questions you missed (ids):")
            print(", ".join(r["id"] for r in wrong))

    if not no_save and total:
        save_progress({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "mode": mode,
            "course": course_label,
            "total": total,
            "correct": correct,
            "pct": round(pct, 1),
            "seconds": int(elapsed),
            "details": results,
        })
        print(f"(saved to {PROGRESS_FILE.name})")


def main():
    ap = argparse.ArgumentParser(description="MCQ drill & mock exam engine")
    ap.add_argument("--bank", default=str(DEFAULT_BANK), help="Question bank JSON")
    ap.add_argument("--course", help="Course code to drill, e.g. BLII-012")
    ap.add_argument("--all", action="store_true", help="Mix questions from all courses")
    ap.add_argument("--count", type=int, default=None, help="Number of questions (default: 10 drill / 50 mock)")
    ap.add_argument("--mock", action="store_true", help="Mock exam mode (no feedback until end)")
    ap.add_argument("--no-save", action="store_true", help="Do not write progress.json")
    ap.add_argument("--report", action="store_true", help="Show progress history and exit")
    ap.add_argument("--selftest", action="store_true", help="Validate the question bank and exit")
    ap.add_argument("--seed", type=int, default=None, help="Random seed (repeatable drills)")
    args = ap.parse_args()

    if args.report:
        show_report()
        return

    questions, errors = load_bank(args.bank)
    if args.selftest:
        if errors:
            print("SELFTEST FAIL:")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        courses = sorted(set(q["course"] for q in questions))
        print(f"SELFTEST PASS: {len(questions)} questions valid across {len(courses)} courses: {', '.join(courses)}")
        sys.exit(0)
    if errors:
        print("Question bank has problems:")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)

    if args.all:
        pool = questions
        label = "ALL"
    elif args.course:
        want = args.course.upper().replace("_", "-")
        pool = [q for q in questions if q["course"].upper() == want]
        label = want
        if not pool:
            available = sorted(set(q["course"] for q in questions))
            raise SystemExit(f"No questions for {want}. Available: {', '.join(available)}")
    else:
        raise SystemExit("Pick --course <CODE> or --all (or --report / --selftest).")

    default_count = 50 if args.mock else 10
    count = args.count or default_count
    random.shuffle(pool)
    selected = pool[:count]
    if len(selected) < count:
        print(f"[!] Only {len(selected)} questions available for {label} (wanted {count}).")

    run_quiz(selected, label, "MOCK EXAM" if args.mock else "DRILL", args.mock, args.no_save)


if __name__ == "__main__":
    main()
