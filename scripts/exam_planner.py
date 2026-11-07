#!/usr/bin/env python3
"""
Exam Prep Planner & Curriculum Triage Engine
Generates tailored study roadmaps, calculates remaining preparation time,
and classifies syllabus topics into Pareto Tiers (Tier 1 Core vs Tier 2 Foundations).
"""

import sys
import argparse
import json
from datetime import datetime, date

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def calculate_time_metrics(exam_date_str, daily_hours=3.0, current_date=None):
    if current_date is None:
        today = date.today()
    elif isinstance(current_date, str):
        today = datetime.strptime(current_date, "%Y-%m-%d").date()
    else:
        today = current_date

    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    days_remaining = (exam_date - today).days

    if days_remaining < 0:
        raise ValueError(f"Exam date {exam_date} is in the past! Current date is {today}.")

    total_study_hours = days_remaining * daily_hours

    if days_remaining <= 7:
        strategy_mode = "Emergency Crunch (1-7 Days)"
        tier1_pct = 0.70
        tier2_pct = 0.30
        tier3_pct = 0.00
    elif days_remaining <= 30:
        strategy_mode = "Tactical Sprint (1-4 Weeks)"
        tier1_pct = 0.60
        tier2_pct = 0.30
        tier3_pct = 0.10
    else:
        strategy_mode = "Comprehensive Mastery (>1 Month)"
        tier1_pct = 0.50
        tier2_pct = 0.35
        tier3_pct = 0.15

    return {
        "today": str(today),
        "exam_date": str(exam_date),
        "days_remaining": days_remaining,
        "daily_hours": daily_hours,
        "total_study_hours": total_study_hours,
        "strategy_mode": strategy_mode,
        "allocation_percentages": {
            "tier1": tier1_pct,
            "tier2": tier2_pct,
            "tier3": tier3_pct
        }
    }

def triage_syllabus(chapters, total_study_hours, allocation_pcts):
    """
    Classify chapters into Tier 1, Tier 2, and Tier 3 based on weightage / historical frequency.
    chapters: list of dicts: [{"name": "...", "weight": int_or_float, "difficulty": "easy/med/hard"}]
    """
    sorted_chapters = sorted(chapters, key=lambda x: x.get("weight", 10), reverse=True)
    total_weight = sum(c.get("weight", 10) for c in sorted_chapters)

    running_weight = 0
    tier1 = []
    tier2 = []
    tier3 = []

    for c in sorted_chapters:
        w = c.get("weight", 10)
        pct_of_total = (w / total_weight) if total_weight > 0 else 0
        running_weight += pct_of_total

        if running_weight <= 0.65 or len(tier1) < max(1, len(sorted_chapters) // 3):
            tier1.append(c)
        elif running_weight <= 0.90:
            tier2.append(c)
        else:
            tier3.append(c)

    # Distribute study hours
    tier1_hours = total_study_hours * allocation_pcts["tier1"]
    tier2_hours = total_study_hours * allocation_pcts["tier2"]
    tier3_hours = total_study_hours * allocation_pcts["tier3"]

    for c in tier1:
        c["allocated_hours"] = round(tier1_hours / max(1, len(tier1)), 1)
        c["target_depth"] = "Deep Mastery (100%): Full theory, derivations, edge cases, PYQs"
        c["tier"] = "Tier 1: Core High-Yield (Guarantees 60-70% Marks)"

    for c in tier2:
        c["allocated_hours"] = round(tier2_hours / max(1, len(tier2)), 1)
        c["target_depth"] = "Safety Net Foundation (40%): Core definitions, key formulas, 1 plug-in example"
        c["tier"] = "Tier 2: Foundation & Safety Net (Buffer for 20-30% Marks)"

    for c in tier3:
        c["allocated_hours"] = round(tier3_hours / max(1, len(tier3)), 1)
        c["target_depth"] = "Quick Skim (10%): 1-page formula sheet & key terms"
        c["tier"] = "Tier 3: Bonus / Edge Cases"

    return {
        "tier1": tier1,
        "tier2": tier2,
        "tier3": tier3,
        "tier1_total_hours": round(tier1_hours, 1),
        "tier2_total_hours": round(tier2_hours, 1),
        "tier3_total_hours": round(tier3_hours, 1)
    }

def format_study_plan_markdown(meta, triaged):
    lines = []
    lines.append(f"# Curated Exam Preparation Roadmap")
    lines.append(f"**Exam Date:** `{meta['exam_date']}` | **Today:** `{meta['today']}` | **Days Remaining:** **{meta['days_remaining']} days**")
    lines.append(f"**Total Available Study Time:** `{meta['total_study_hours']:.1f} hours` (at `{meta['daily_hours']:.1f} hrs/day`)")
    lines.append(f"**Selected Strategy Mode:** `{meta['strategy_mode']}`\n")

    lines.append("## Executive Strategy: The Pareto Tiers")
    lines.append("> **Why this works:** Rather than rushing superficially through the entire syllabus or skipping whole chapters, we split study effort into **Deep Mastery (Tier 1)** to guarantee the bulk of exam marks, paired with **High-Leverage Foundations (Tier 2)** so no question on remaining chapters blindsides you.\n")

    lines.append("### Tier 1: Core High-Yield (Target: 60% - 70% of Marks)")
    lines.append(f"*Total Time Allocated: {triaged['tier1_total_hours']} hours*")
    lines.append("| Chapter / Topic | Weightage | Target Hours | Study Protocol |")
    lines.append("| :--- | :---: | :---: | :--- |")
    for c in triaged["tier1"]:
        lines.append(f"| **{c['name']}** | {c.get('weight', 'N/A')}% | `{c['allocated_hours']} hrs` | Master all past exam questions, edge cases, step-by-step problem templates |")
    lines.append("")

    lines.append("### Tier 2: Foundation & Safety Net (Target: 20% - 30% of Marks)")
    lines.append(f"*Total Time Allocated: {triaged['tier2_total_hours']} hours*")
    lines.append("| Chapter / Topic | Weightage | Target Hours | Safety Net Protocol |")
    lines.append("| :--- | :---: | :---: | :--- |")
    for c in triaged["tier2"]:
        lines.append(f"| **{c['name']}** | {c.get('weight', 'N/A')}% | `{c['allocated_hours']} hrs` | 3 core definitions, 2 fundamental formulas, 1 standard plug-in example |")
    lines.append("")

    if triaged["tier3"]:
        lines.append("### Tier 3: Bonus / Quick Skim")
        lines.append(f"*Total Time Allocated: {triaged['tier3_total_hours']} hours*")
        for c in triaged["tier3"]:
            lines.append(f"- **{c['name']}** ({c.get('weight', 'N/A')}%) – `{c['allocated_hours']} hrs`: 1-page formula sheet & key definitions.")
        lines.append("")

    lines.append("## Daily Time Allocation Recipe")
    lines.append("- **50% New Intake & Intuitive Grasp:** Read Feynman-style breakdown, understand physical meaning.")
    lines.append("- **35% Active Execution & PYQ Practice:** Solve past exam problems on paper without peeking at answers.")
    lines.append("- **15% Active Recall & Retention:** 5-minute rapid-fire self-quizzing before closing books.")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Curate exam preparation roadmap based on time remaining.")
    parser.add_argument("--exam-date", required=True, help="Exam date in YYYY-MM-DD format")
    parser.add_argument("--current-date", default=None, help="Current date in YYYY-MM-DD format (defaults to today)")
    parser.add_argument("--daily-hours", type=float, default=3.0, help="Available study hours per day")
    parser.add_argument("--syllabus", help="JSON file or string containing chapter list with weights")
    args = parser.parse_args()

    metrics = calculate_time_metrics(args.exam_date, args.daily_hours, args.current_date)

    if args.syllabus:
        try:
            if args.syllabus.endswith(".json"):
                with open(args.syllabus, "r") as f:
                    chapters = json.load(f)
            else:
                chapters = json.loads(args.syllabus)
        except Exception as e:
            print(f"Error parsing syllabus: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default sample syllabus for demonstration
        chapters = [
            {"name": "Chapter 1: Foundational Principles & Terminology", "weight": 10},
            {"name": "Chapter 2: Main Analytical Frameworks (High-Yield)", "weight": 30},
            {"name": "Chapter 3: Procedural Systems & Classification/Methods", "weight": 25},
            {"name": "Chapter 4: Advanced Problem Solving & Case Applications", "weight": 20},
            {"name": "Chapter 5: Contemporary Trends & Supplementary Topics", "weight": 15}
        ]

    triaged = triage_syllabus(chapters, metrics["total_study_hours"], metrics["allocation_percentages"])
    md_output = format_study_plan_markdown(metrics, triaged)
    print(md_output)

if __name__ == "__main__":
    main()
