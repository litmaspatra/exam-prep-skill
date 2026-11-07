#!/usr/bin/env python3
"""
Exam Prep Planner & Curriculum Triage Engine

Generates tailored study roadmaps, calculates remaining preparation time,
and classifies syllabus topics into Pareto Tiers (Tier 1 Core vs Tier 2
Foundations vs Tier 3 Skim).

Two modes:
  * Single exam : --exam-date YYYY-MM-DD with a flat syllabus JSON
                  (a list of {"name", "weight", "difficulty"} chapters).
  * Multi-exam  : any exam profile (profiles/<exam>.json) with several papers,
                  each with its own exam_date. Produces one Pareto plan per
                  paper plus a day-by-day calendar that schedules study hours
                  earliest-exam-first.
"""

import sys
import argparse
import json
from datetime import datetime, date, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def strategy_for_days(days_remaining):
    if days_remaining <= 7:
        return "Emergency Crunch (1-7 Days)", (0.70, 0.30, 0.00)
    if days_remaining <= 30:
        return "Tactical Sprint (1-4 Weeks)", (0.60, 0.30, 0.10)
    return "Comprehensive Mastery (>1 Month)", (0.50, 0.35, 0.15)


def triage_units(units, total_study_hours, pcts):
    """Split units into Tier 1/2/3 by cumulative weight share.

    Tier 1 always holds at least the single highest-weight unit; further
    units join only while Tier 1's cumulative share stays within 65%.
    Tier 2 covers up to 90% cumulative share; the rest is Tier 3.
    """
    sorted_units = sorted(units, key=lambda u: u.get("weight", 10), reverse=True)
    total_weight = sum(u.get("weight", 10) for u in sorted_units) or 1

    tiers = {"Tier 1": [], "Tier 2": [], "Tier 3": []}
    running = 0.0
    for u in sorted_units:
        share = u.get("weight", 10) / total_weight
        hint = u.get("tier_hint")  # optional 1/2/3 pin in the syllabus JSON
        if hint in (1, 2, 3):
            tiers[f"Tier {hint}"].append(u)
        elif not tiers["Tier 1"] or running + share <= 0.65:
            tiers["Tier 1"].append(u)
        elif running + share <= 0.90:
            tiers["Tier 2"].append(u)
        else:
            tiers["Tier 3"].append(u)
        running += share

    hours = {
        "Tier 1": total_study_hours * pcts[0],
        "Tier 2": total_study_hours * pcts[1],
        "Tier 3": total_study_hours * pcts[2],
    }
    depth = {
        "Tier 1": "Deep Mastery (100%): full theory, edge cases, every past exam question",
        "Tier 2": "Safety Net (40%): 3 core definitions, 2 key rules/formulas, 1 standard example",
        "Tier 3": "Quick Skim (10%): 1-page formula & keyword sheet",
    }
    for tier_name, members in tiers.items():
        per_unit = round(hours[tier_name] / max(1, len(members)), 1) if members else 0.0
        for u in members:
            u["allocated_hours"] = per_unit
            u["tier"] = tier_name
            u["target_depth"] = depth[tier_name]

    return tiers, {k: round(v, 1) for k, v in hours.items()}


# ---------------------------------------------------------------------------
# Single-exam (legacy flat syllabus) mode
# ---------------------------------------------------------------------------

def format_single_plan(meta, tiers, tier_hours):
    lines = []
    lines.append("# Curated Exam Preparation Roadmap")
    lines.append(f"**Exam Date:** `{meta['exam_date']}` | **Today:** `{meta['today']}` | **Days Remaining:** **{meta['days_remaining']} days**")
    lines.append(f"**Total Available Study Time:** `{meta['total_hours']:.1f} hours` (at `{meta['daily_hours']:.1f} hrs/day`)")
    lines.append(f"**Selected Strategy Mode:** `{meta['strategy_mode']}`\n")

    lines.append("## Executive Strategy: The Pareto Tiers")
    lines.append("> **Why this works:** Rather than rushing superficially through the entire syllabus or skipping whole chapters, effort is split into **Deep Mastery (Tier 1)** to secure the bulk of exam marks, paired with **High-Leverage Foundations (Tier 2)** so no question on remaining chapters blindsides you.\n")

    labels = {
        "Tier 1": "### Tier 1: Core High-Yield (Target: 60% - 70% of Marks)",
        "Tier 2": "### Tier 2: Foundation & Safety Net (Target: 20% - 30% of Marks)",
        "Tier 3": "### Tier 3: Bonus / Quick Skim",
    }
    for tier_name in ("Tier 1", "Tier 2", "Tier 3"):
        members = tiers[tier_name]
        if not members:
            continue
        lines.append(labels[tier_name])
        lines.append(f"*Total Time Allocated: {tier_hours[tier_name]} hours*")
        lines.append("| Chapter / Topic | Weightage | Target Hours | Study Protocol |")
        lines.append("| :--- | :---: | :---: | :--- |")
        for u in members:
            lines.append(f"| **{u['name']}** | {u.get('weight', 'N/A')}% | `{u['allocated_hours']} hrs` | {u['target_depth']} |")
        lines.append("")

    lines.append("## Daily Time Allocation Recipe")
    lines.append("- **50% New Intake & Intuitive Grasp:** Read Feynman-style breakdown, understand the meaning.")
    lines.append("- **35% Active Execution & PYQ Practice:** Solve past exam questions without peeking at answers.")
    lines.append("- **15% Active Recall & Retention:** 5-minute rapid-fire self-quizzing before closing books.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Multi-exam mode
# ---------------------------------------------------------------------------

def plan_course(course, daily_hours, today, total_hours):
    exam = parse_date(course["exam_date"])
    days = (exam - today).days
    if days < 0:
        raise SystemExit(f"Exam date {exam} for {course.get('code', course.get('name'))} is in the past (today is {today}).")
    mode, pcts = strategy_for_days(days)
    tiers, tier_hours = triage_units(course.get("units", []), total_hours, pcts)
    return {
        "code": course.get("code", course.get("name", "Course")),
        "name": course.get("name", ""),
        "exam_date": exam,
        "days_remaining": days,
        "total_hours": total_hours,
        "strategy_mode": mode,
        "tiers": tiers,
        "tier_hours": tier_hours,
    }


def build_calendar(course_plans, daily_hours, today):
    """Earliest-deadline-first scheduling of unit-level study blocks."""
    queues = {}
    exams = {}
    for cp in course_plans:
        exams[cp["code"]] = cp["exam_date"]
        q = []
        for tier_name in ("Tier 1", "Tier 2", "Tier 3"):
            for u in cp["tiers"][tier_name]:
                q.append({"course": cp["code"], "tier": tier_name,
                          "unit": u["name"], "hours": float(u["allocated_hours"])})
        queues[cp["code"]] = q

    last_exam = max(cp["exam_date"] for cp in course_plans)
    calendar = []
    day = today
    exam_days = set(exams.values())
    while day <= last_exam:
        capacity = float(daily_hours)
        entries = []
        while capacity > 0.01 and day not in exam_days:
            eligible = [c for c, q in queues.items() if q and day < exams[c]]
            if not eligible:
                break
            code = min(eligible, key=lambda c: exams[c])
            task = queues[code][0]
            take = round(min(capacity, task["hours"]), 2)
            entries.append({"course": code, "tier": task["tier"], "unit": task["unit"], "hours": take})
            task["hours"] = round(task["hours"] - take, 2)
            if task["hours"] <= 0.01:
                queues[code].pop(0)
            capacity = round(capacity - take, 2)
        if entries:
            calendar.append({"date": day, "entries": entries})
        day += timedelta(days=1)

    leftover = [(code, t) for code, q in queues.items() for t in q]
    return calendar, leftover


def format_multi_plan(program, session, course_plans, calendar, leftover, daily_hours, today, fmt="mcq"):
    lines = []
    title = program or "Multi-Exam Preparation"
    if session:
        title += f" — {session}"
    lines.append(f"# Curated Exam Preparation Roadmap: {title}")
    lines.append(f"**Today:** `{today}` | **Daily Study Time:** `{daily_hours:.1f} hrs/day`")
    exam_bits = [f"**{cp['code']}** on `{cp['exam_date']}` ({cp['days_remaining']}d)" for cp in course_plans]
    lines.append("**Exams:** " + " · ".join(exam_bits) + "\n")

    for cp in course_plans:
        lines.append(f"## {cp['code']} — {cp['name']}")
        lines.append(f"*Exam `{cp['exam_date']}` | {cp['days_remaining']} days left | ~{cp['total_hours']:.1f} hours | Mode: {cp['strategy_mode']}*\n")
        for tier_name in ("Tier 1", "Tier 2", "Tier 3"):
            members = cp["tiers"][tier_name]
            if not members:
                continue
            label = {"Tier 1": "Tier 1: Core High-Yield", "Tier 2": "Tier 2: Safety Net", "Tier 3": "Tier 3: Quick Skim"}[tier_name]
            lines.append(f"### {label} ({cp['tier_hours'][tier_name]} hrs)")
            lines.append("| Unit | Weight | Hours | Protocol |")
            lines.append("| :--- | :---: | :---: | :--- |")
            for u in members:
                lines.append(f"| {u['name']} | {u.get('weight', 'N/A')}% | `{u['allocated_hours']} hrs` | {u['target_depth']} |")
            lines.append("")

    lines.append("## Day-by-Day Calendar (earliest exam scheduled first)")
    lines.append("| Date | Day | Study Blocks |")
    lines.append("| :--- | :--- | :--- |")
    for row in calendar:
        blocks = []
        for e in row["entries"]:
            unit = e["unit"] if len(e["unit"]) <= 60 else e["unit"][:57] + "..."
            blocks.append(f"{e['course']} {e['tier']}: {unit} ({e['hours']:.1f}h)")
        lines.append(f"| {row['date']} | {row['date'].strftime('%a')} | {' + '.join(blocks)} |")
    for cp in course_plans:
        lines.append(f"| {cp['exam_date']} | {cp['exam_date'].strftime('%a')} | **{cp['code']} EXAM DAY** |")
    lines.append("")

    if leftover:
        lines.append("> **Warning:** not enough days to schedule everything at this daily load:")
        for code, t in leftover:
            lines.append(f"> - {code} {t['tier']}: {t['unit']} ({t['hours']:.1f}h unscheduled)")
        lines.append("> Increase --daily-hours or accept a lighter Tier 3.\n")

    lines.append("## Daily Time Allocation Recipe")
    lines.append("- **50% New Intake:** read the study material / simplified breakdown for the scheduled unit.")
    if fmt == "descriptive":
        lines.append("- **35% PYQ Practice:** write out past-paper answers by hand, timed, no peeking.")
    else:
        lines.append("- **35% PYQ & MCQ Practice:** run `python scripts/mcq_quiz.py --profile <exam> --course <CODE> --count 15`.")
    lines.append("- **15% Active Recall:** rapid-fire self-quiz from the 1-page cheat sheet.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------

def load_syllabus(arg):
    if arg is None:
        return None
    candidate = Path(arg)
    if candidate.exists() and candidate.suffix == ".json":
        return json.loads(candidate.read_text(encoding="utf-8"))
    # resolve a profile id/name from profiles/
    prof_dir = Path(__file__).resolve().parent.parent / "profiles"
    for f in sorted(prof_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if arg.lower() in (d.get("id", "").lower(), f.stem.lower(), d.get("name", "").lower()):
            return d
    return json.loads(arg)


def main():
    parser = argparse.ArgumentParser(description="Curate exam preparation roadmap based on time remaining.")
    parser.add_argument("--exam-date", help="Single exam date YYYY-MM-DD (flat syllabus mode)")
    parser.add_argument("--current-date", default=None, help="Override 'today' (YYYY-MM-DD), for testing")
    parser.add_argument("--daily-hours", type=float, default=3.0, help="Available study hours per day")
    parser.add_argument("--syllabus", "--profile", dest="syllabus",
                        help="Exam profile / syllabus JSON file or string (flat chapter list OR profile with papers)")
    args = parser.parse_args()

    today = parse_date(args.current_date) if args.current_date else date.today()
    syllabus = load_syllabus(args.syllabus)

    if isinstance(syllabus, dict) and ("papers" in syllabus or "courses" in syllabus):
        # Multi-exam mode (profile file or structured syllabus)
        if args.exam_date:
            print("[!] --exam-date is ignored in multi-paper mode; dates come from each paper.", file=sys.stderr)
        courses = sorted(syllabus.get("papers") or syllabus["courses"], key=lambda c: c["exam_date"])
        # The study pool is one shared capacity (today -> last exam), split
        # across courses in proportion to their total unit weight.
        last_exam = max(parse_date(c["exam_date"]) for c in courses)
        pool = args.daily_hours * max(0, (last_exam - today).days)
        weights = [sum(u.get("weight", 10) for u in c.get("units", [])) or 1 for c in courses]
        total_weight = sum(weights)
        plans = [plan_course(c, args.daily_hours, today, pool * w / total_weight)
                 for c, w in zip(courses, weights)]
        calendar, leftover = build_calendar(plans, args.daily_hours, today)
        leftover = [(c, t) for c, t in leftover if t["hours"] > 0.5]
        label = syllabus.get("name") or syllabus.get("program")
        print(format_multi_plan(label, syllabus.get("exam_session"),
                                plans, calendar, leftover, args.daily_hours, today,
                                syllabus.get("format", "mcq")))
        return

    # Single-exam flat mode
    if not args.exam_date:
        raise SystemExit("--exam-date is required when the syllabus is a flat chapter list.")
    exam = parse_date(args.exam_date)
    days = (exam - today).days
    if days < 0:
        raise SystemExit(f"Exam date {exam} is in the past (today is {today}).")
    mode, pcts = strategy_for_days(days)
    total_hours = days * args.daily_hours

    if syllabus is None:
        syllabus = [
            {"name": "Chapter 1: Foundational Principles & Terminology", "weight": 10},
            {"name": "Chapter 2: Main Analytical Frameworks (High-Yield)", "weight": 30},
            {"name": "Chapter 3: Procedural Systems & Classification/Methods", "weight": 25},
            {"name": "Chapter 4: Advanced Problem Solving & Case Applications", "weight": 20},
            {"name": "Chapter 5: Contemporary Trends & Supplementary Topics", "weight": 15},
        ]
    tiers, tier_hours = triage_units(syllabus, total_hours, pcts)
    meta = {"today": str(today), "exam_date": str(exam), "days_remaining": days,
            "daily_hours": args.daily_hours, "total_hours": total_hours, "strategy_mode": mode}
    print(format_single_plan(meta, tiers, tier_hours))


if __name__ == "__main__":
    main()
