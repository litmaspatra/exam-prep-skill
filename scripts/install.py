#!/usr/bin/env python3
"""
Universal Multi-Platform Installer for Exam Prep Skill
Installs the exam-prep skill across:
- Google Antigravity (global config)
- Anthropic Claude Code (CLI commands / CLAUDE.md)
- Cursor AI & Windsurf (.cursorrules)
- Cline & Roo Code (.clinerules)
- Nous Research Hermes (Hermes Agent / skill config)
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Fix Windows console UTF-8 output if needed
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent

def install_antigravity(target_dir=None):
    home = Path.home()
    if target_dir:
        dest = Path(target_dir)
    else:
        dest = home / ".gemini" / "config" / "skills" / "exam-prep"
    
    src = REPO_ROOT / ".agents" / "skills" / "exam-prep"
    if not src.exists():
        src = REPO_ROOT
    
    print(f"[+] Installing for Antigravity at: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    
    # Copy SKILL.md, references, scripts, templates
    for item in ["SKILL.md", "references", "scripts", "templates", "data"]:
        s = src / item
        d = dest / item
        if s.exists():
            if s.is_dir():
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
    print("    ✓ Antigravity skill installed successfully!")

def install_claude_code(target_dir=None):
    home = Path.home()
    if target_dir:
        dest = Path(target_dir)
    else:
        dest = home / ".claude" / "commands"
    
    print(f"[+] Installing for Claude Code at: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    
    src_cmd = REPO_ROOT / ".claude" / "commands" / "exam-prep.md"
    if src_cmd.exists():
        shutil.copy2(src_cmd, dest / "exam-prep.md")
    
    # Also copy CLAUDE.md to current working directory if not present
    cwd_claude = Path.cwd() / "CLAUDE.md"
    if not cwd_claude.exists() and (REPO_ROOT / "CLAUDE.md").exists():
        shutil.copy2(REPO_ROOT / "CLAUDE.md", cwd_claude)
        print(f"    ✓ Placed CLAUDE.md in current directory: {cwd_claude}")
    print("    ✓ Claude Code configuration installed successfully!")

def install_cursor(target_dir=None):
    dest = Path(target_dir) if target_dir else Path.cwd()
    print(f"[+] Installing for Cursor / Windsurf at: {dest}")
    src = REPO_ROOT / ".cursorrules"
    if src.exists():
        shutil.copy2(src, dest / ".cursorrules")
        print("    ✓ .cursorrules installed successfully!")

def install_cline(target_dir=None):
    dest = Path(target_dir) if target_dir else Path.cwd()
    print(f"[+] Installing for Cline / Roo Code at: {dest}")
    src = REPO_ROOT / ".clinerules"
    if src.exists():
        shutil.copy2(src, dest / ".clinerules")
        print("    ✓ .clinerules installed successfully!")

def install_hermes(target_dir=None):
    home = Path.home()
    dest = Path(target_dir) if target_dir else home / ".hermes" / "skills" / "exam-prep"
    print(f"[+] Installing for Hermes Agent at: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    
    src = REPO_ROOT / "hermes"
    if src.exists():
        for f in src.iterdir():
            shutil.copy2(f, dest / f.name)
    print("    ✓ Hermes skill files installed successfully!")

def main():
    parser = argparse.ArgumentParser(description="Multi-platform installer for Exam Prep Skill")
    parser.add_argument("--all", action="store_true", help="Install to all supported platforms")
    parser.add_argument("--antigravity", action="store_true", help="Install to Google Antigravity")
    parser.add_argument("--claude", action="store_true", help="Install to Anthropic Claude Code")
    parser.add_argument("--cursor", action="store_true", help="Install to Cursor AI / Windsurf")
    parser.add_argument("--cline", action="store_true", help="Install to Cline / Roo Code")
    parser.add_argument("--hermes", action="store_true", help="Install to Hermes Agent")
    parser.add_argument("--target-dir", help="Custom target directory for installation")

    args = parser.parse_args()

    if not any([args.all, args.antigravity, args.claude, args.cursor, args.cline, args.hermes]):
        parser.print_help()
        print("\n[!] Please specify at least one platform flag (e.g., --all, --claude, --antigravity, --hermes, --cursor)")
        sys.exit(1)

    print("==================================================")
    print("🎓 Exam Prep Skill: Multi-Platform Installer")
    print("==================================================")

    if args.all or args.antigravity:
        install_antigravity(args.target_dir)
    if args.all or args.claude:
        install_claude_code(args.target_dir)
    if args.all or args.cursor:
        install_cursor(args.target_dir)
    if args.all or args.cline:
        install_cline(args.target_dir)
    if args.all or args.hermes:
        install_hermes(args.target_dir)

    print("\n🎉 Installation completed successfully!")

if __name__ == "__main__":
    main()
