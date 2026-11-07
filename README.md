# 🎓 Exam Prep & Curriculum Mastery Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Antigravity](https://img.shields.io/badge/Antigravity-Native%20Skill-brightgreen.svg)]()
[![Platform: Claude Code](https://img.shields.io/badge/Claude%20Code-Supported-blueviolet.svg)]()
[![Platform: Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Supported-orange.svg)]()
[![Platform: Codex / ChatGPT](https://img.shields.io/badge/Codex%20%2F%20ChatGPT-Compatible-teal.svg)]()
[![Platform: Cursor & Cline](https://img.shields.io/badge/Cursor%20%26%20Cline-Ready-yellowgreen.svg)]()

An intelligent, multi-platform exam preparation and curriculum acceleration skill for AI coding agents. It ingests your exam name, institution, syllabus, and target exam date, researches past year question papers (PYQs) online, curates a time-budgeted study roadmap using the Pareto 80/20 principle, and breaks down complex concepts (mathematics, classification systems like Dewey Decimal Classification, technical topics) using Feynman first-principles intuition.

---

## 🌟 Key Features

0. **Deterministic Official Material Fetching (IGNOU):** `scripts/fetch_materials.py` downloads previous year question papers (webservices.ignou.ac.in) and full study material (eGyankosh) - official, free, no login, resumable.
1. **Automated PYQ & Blueprint Intelligence:**
   - Researches previous year question papers (PYQs), marking schemes, and recurring question archetypes for specific universities (IGNOU, DU, Anna Univ, etc.) or standardized exams (GATE, GRE).
   - Identifies whether the exam is descriptive or objective (e.g. OMR/MCQs) to tailor your study strategy.
2. **Time-Aware Curriculum Curation (Pareto 80/20 Triage):**
   - **Tier 1: Core High-Yield (60%–70% Marks):** Deep mastery of the top 20–30% topics that recur every year.
   - **Tier 2: Foundation & Safety Net (20%–30% Marks — Never Skipped!):** For the remaining 70% of the syllabus, you learn the **Core 3**: 3 essential definitions, 2 basic formulas/rules, and 1 real-world analogy. If an exam question appears on these topics, you snag 70–80% partial or full marks.
   - **Tier 3: Bonus / Quick Skim:** 1-page formula & keyword recap.
3. **Intuitive First-Principles Teaching:**
   - **Mathematics & Quantitative:** Physical intuition $\to$ Minimal formula $\to$ 3-step benchmark problem $\to$ Exam trap alert.
   - **Classification Systems & Taxonomies (e.g., Dewey Decimal Classification - DDC):** Must-memorize code bank, 10-class story mnemonic, 3-step decision algorithms, and practice drills.
4. **MCQ Drill & Mock Exam Engine:** `scripts/mcq_quiz.py` runs option-shuffled drills and 50-question OMR mock simulations per course, with explanations and a persistent `progress.json` score history.
5. **Multi-Exam Planning:** the planner handles several courses with staggered exam dates (e.g. IGNOU CLIS Dec 2026: BLI-011/BLII-012/013/014), splits the shared study pool across courses, and emits a day-by-day calendar.
6. **Actionable Revision Artifacts:**
   - Rapid-fire active recall drills.
   - 1-Page Master Cheat Sheets for the final 24-hour review.
   - Predicted Mock Exam Papers matching official university marking schemes.

---

## 🚀 Multi-Platform Installation Guide

Clone this repository:
```bash
git clone https://github.com/litmaspatra/exam-prep-skill.git
cd exam-prep-skill
```

### 1. One-Click Universal Installer
Run the included python installer to set up all your AI agents automatically:
```bash
# Install to all supported platforms at once
python scripts/install.py --all

# Or target specific platforms:
python scripts/install.py --claude        # Claude Code
python scripts/install.py --antigravity   # Google Antigravity
python scripts/install.py --hermes        # Hermes Agent
python scripts/install.py --cursor        # Cursor / Windsurf
python scripts/install.py --cline         # Cline / Roo Code
```

---

### 2. Manual Platform Setup

#### 🟣 Anthropic Claude Code (`claude` CLI)
* **Project Level:** Keep `CLAUDE.md` in your project root or workspace. Claude Code automatically reads it upon launch.
* **Global Slash Command:** Copy `.claude/commands/exam-prep.md` to `~/.claude/commands/exam-prep.md`. You can then run `/exam-prep` directly in Claude Code chat.

#### 🟠 Nous Research Hermes (`hermes-agent` / Function Calling)
* Copy the files in `hermes/` to your Hermes skills or agents folder:
  ```bash
  cp hermes/* ~/.hermes/skills/exam-prep/
  ```
* Include `hermes/hermes_prompt.txt` as a system prompt and `hermes/hermes_skill.json` as a callable function/tool.

#### 🟢 Google Antigravity / Gemini CLI
* Native skill format with YAML frontmatter.
* Copy `.agents/skills/exam-prep` to `~/.gemini/config/skills/exam-prep` for global availability across all workspaces.

#### 🔵 OpenAI Codex / ChatGPT / OpenAI Assistant API
* Open `codex/codex_instructions.md` and copy the instructions directly into your ChatGPT Custom Instructions, Custom GPT system prompt, or OpenAI Assistant configuration.

#### ⚡ Cursor AI & Windsurf
* The repository includes a ready-to-use `.cursorrules` file. Copy it to any project workspace to enable exam prep capabilities in Cursor chat (`Ctrl+L` / `Cmd+L`).

#### 🛠️ Cline / Roo Code
* Includes a pre-configured `.clinerules` file for autonomous task execution and test preparation planning.

---

## 📂 Repository Structure

```text
exam-prep-skill/
├── .agents/skills/exam-prep/        # Native Google Antigravity & AGY Skill
│   ├── SKILL.md                  # Main Skill Instruction & Workflow
│   ├── references/               # Deep-dive guides
│   │   ├── pyq-search-strategies.md  # Web search query templates for PYQs
│   │   ├── pedagogy-guides.md        # Math, DDC & concept simplification guides
│   │   └── curriculum-triage.md      # Mathematical Pareto time allocation
│   ├── scripts/
│   │   └── exam_planner.py           # Automated CLI roadmap generator
│   └── templates/
│       ├── study-plan-template.md    # Curated syllabus markdown template
│       ├── cheat-sheet-template.md   # 1-Page master revision template
│       └── mock-paper-template.md    # University-style mock test template
├── .claude/                         # Claude Code configuration
│   └── commands/
│       └── exam-prep.md          # /exam-prep custom command
├── CLAUDE.md                        # Claude Code native project memory & rules
├── .cursorrules                     # Cursor AI IDE rule
├── .clinerules                      # Cline / Roo Code / VS Code AI agents
├── hermes/                          # Nous Research Hermes / Hermes-Agent
│   ├── hermes_prompt.txt            # System prompt for Hermes
│   └── hermes_skill.json            # Skill schema for Hermes agent workflows
├── codex/                           # OpenAI Codex / GPT-4o / ChatGPT Custom Instructions
│   └── codex_instructions.md        # Custom instruction prompt
├── scripts/
│   ├── exam_planner.py              # CLI planner (single-exam + multi-exam calendar)
│   ├── fetch_materials.py           # Official IGNOU PYQ + SLM downloader
│   ├── mcq_quiz.py                  # MCQ drill & mock exam engine (progress.json)
│   └── install.py                   # Multi-platform universal installer
├── data/
│   └── clis_mcq_bank.json           # Seed MCQ bank (grow it from fetched PYQs)
├── examples/
│   ├── dewey-decimal-classification-mastery.md  # Concrete DDC teaching case study
│   ├── curated-1-month-plan-sample.md           # Concrete 30-day Pareto sprint plan
│   └── ignou-clis-exam-blueprint.md             # Real IGNOU CLIS exam intelligence
├── LICENSE                          # MIT License
└── README.md
```

---

## ⚡ CLI Tool Usage

Generate an instant time-budgeted study breakdown directly from your terminal:

```bash
# Single exam: 34 days remaining, 3 hours/day
python scripts/exam_planner.py --exam-date 2026-12-11 --daily-hours 3.0

# Multi-exam structured syllabus (IGNOU CLIS Dec 2026, 4 papers):
python scripts/exam_planner.py --syllabus ignou_clis_syllabus.json --daily-hours 3.0
```

### IGNOU CLIS Quickstart
```bash
python scripts/fetch_materials.py                          # official PYQs + study material -> materials/
python scripts/exam_planner.py --syllabus ignou_clis_syllabus.json --daily-hours 3.0   # full Dec 2026 plan
python scripts/mcq_quiz.py --course BLII-012 --count 15    # drill one paper
python scripts/mcq_quiz.py --course BLI-011 --mock         # 50-question mock
python scripts/mcq_quiz.py --report                        # your score history
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
