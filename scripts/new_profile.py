#!/usr/bin/env python3
"""
Guided creator for a new exam profile (profiles/<id>.json).

    python scripts/new_profile.py

Answers a few questions, then writes:
  * profiles/<id>.json   - papers, dates, format, marking, sources
  * data/<id>-bank.json  - an empty question bank for mcq_quiz.py
"""

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent


def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        ans = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        ans = ""
    return ans or (default or "")


def main():
    print("=== New Exam Profile ===")
    name = ask("Exam / course name (e.g. 'BCom 1st Year', 'GATE CS')")
    if not name:
        raise SystemExit("name is required")
    pid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    pid = ask("Profile id (folder-friendly)", pid)
    institution = ask("University / board / institution")
    session = ask("Exam session (e.g. 'June 2027')", "")
    fmt = ask("Paper format: mcq / descriptive / mixed", "mcq").lower()
    if fmt not in ("mcq", "descriptive", "mixed"):
        fmt = "mixed"
    marks = ask("Marks per paper", "50")
    hours = ask("Duration in hours", "2")

    papers = []
    print("\nAdd papers (one exam date each). Empty code finishes.")
    while True:
        code = ask(f"Paper {len(papers)+1} code (e.g. CS-101)")
        if not code:
            break
        pname = ask("  Paper name", code)
        date = ask("  Exam date (YYYY-MM-DD)")
        units = []
        raw = ask("  Units, comma-separated, optional :weight (e.g. 'Algebra:30, Calculus:40')", "")
        for part in [p.strip() for p in raw.split(",") if p.strip()]:
            if ":" in part:
                uname, w = part.rsplit(":", 1)
                units.append({"name": uname.strip(), "weight": float(w)})
            else:
                units.append({"name": part, "weight": 10})
        papers.append({"code": code, "name": pname, "exam_date": date, "units": units})

    if not papers:
        raise SystemExit("need at least one paper")

    sources = {}
    print("\nMaterial sources (optional):")
    if ask("  Use IGNOU's PYQ archive? (y/n)", "n").lower().startswith("y"):
        ap = ask("  Archive path (school/programme, e.g. 'SOSS/XXXX')")
        yrs = ask("  Year range (e.g. 2020-2025)", "2020-2025")
        fy, _, ty = yrs.partition("-")
        sources["pyq_archive"] = {
            "adapter": "ignou-pyq-archive", "archive_path": ap,
            "codes": [p["code"] for p in papers],
            "from_year": int(fy or 2020), "to_year": int(ty or 2025),
            "sessions": ["June", "December"]}
    if ask("  Crawl a DSpace community for study material? (y/n)", "n").lower().startswith("y"):
        sources["slm_repository"] = {"adapter": "dspace-community",
                                     "community": ask("  Community URL (https://...)")}
    urls = ask("  Extra PDF URLs, comma-separated (or empty)", "")
    if urls:
        sources["url_list"] = [{"url": u.strip()} for u in urls.split(",") if u.strip()]

    profile = {
        "id": pid, "name": name, "institution": institution,
        "exam_session": session, "format": fmt,
        "marking": {"marks_per_paper": int(marks), "duration_hours": float(hours),
                    "negative_marking": False},
        "papers": papers, "sources": sources,
        "mcq_bank": f"data/{pid}-bank.json",
    }
    (REPO_ROOT / "profiles").mkdir(exist_ok=True)
    ppath = REPO_ROOT / "profiles" / f"{pid}.json"
    ppath.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    bpath = REPO_ROOT / "data" / f"{pid}-bank.json"
    if not bpath.exists():
        bpath.write_text(json.dumps({"bank": f"{pid}-bank", "version": 1,
                                     "note": "Add questions: type mcq (options + answer_index) or flashcard (answer).",
                                     "questions": []}, indent=2), encoding="utf-8")
    print(f"\nWrote {ppath.relative_to(REPO_ROOT)} and {bpath.relative_to(REPO_ROOT)}")
    print("\nNext steps:")
    print(f"  python scripts/fetch_materials.py --profile {pid}")
    print(f"  python scripts/exam_planner.py --profile {pid} --daily-hours 3")
    print(f"  python scripts/mcq_quiz.py --profile {pid} --count 10")


if __name__ == "__main__":
    main()
