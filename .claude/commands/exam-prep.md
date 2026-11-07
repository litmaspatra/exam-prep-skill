# /exam-prep

Prepares students for university, board, or licensing examinations through PYQ intelligence, time-budgeted Pareto curriculum curation, and intuitive first-principles teaching.

## Usage
`/exam-prep [Exam Name] [Course] [University] [Exam Date]`

## Workflow
0. For IGNOU, fetch official material first: `python scripts/fetch_materials.py` (PYQs + study material). Grow `data/clis_mcq_bank.json` from the fetched PYQs.
1. Calculate days remaining until the exam.
2. Mine the downloaded PYQs (or search the web as fallback) for weightages.
3. Categorize syllabus into:
   - **Tier 1 (Core High-Yield, 60-70% marks)**
   - **Tier 2 (Safety Net Foundations, 20-30% marks - Never skipped!)**
   - **Tier 3 (Bonus / Skim)**
4. Provide Feynman-style intuitive explanations, math problem-solving templates, and classification code banks.
5. For MCQ/OMR exams run drills and mocks: `python scripts/mcq_quiz.py --course <CODE> --count 15`, `--mock`, `--report`.
6. For staggered multi-paper exams: `python scripts/exam_planner.py --syllabus <structured.json> --daily-hours <H>`.
7. Generate a 1-page master cheat sheet and predicted mock test.
