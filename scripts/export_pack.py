#!/usr/bin/env python
"""Track R: copy the team workbench pack from this kit into a team repo (never overwrites).

Usage (from the team repo root):
    python <kit>/scripts/export_pack.py .                          # asks for the ticket regex
    python <kit>/scripts/export_pack.py . --ticket-regex "(ABC|OPS)-\\d+"

Copies: .claude/agents/verifier.md, .claude/hooks/linkage_guard.py,
.claude/hooks/snippets/linkage.json, scripts/hooks.py, scripts/audit.py,
scripts/pii_scan.py, docs/templates/CLAUDE.template.md; writes .claude/linkage.json.
Existing files are kept (SKIP exists). Exit 0 = done, 2 = bad target or regex.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_REPO = os.path.dirname(HERE)
DEFAULT_REGEX = r"(BOOK|CHG|PLAT|SPEC-BK)-\d+"
FILES = [
    ".claude/agents/verifier.md",
    ".claude/hooks/linkage_guard.py",
    ".claude/hooks/snippets/linkage.json",
    "scripts/hooks.py",
    "scripts/audit.py",
    "scripts/pii_scan.py",
    "docs/templates/CLAUDE.template.md",
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="export_pack.py", description="Copy the workbench pack into a team repo (Track R).")
    ap.add_argument("team_repo", help="path to the team repo (usually .)")
    ap.add_argument("--ticket-regex", help=f"ticket pattern for the linkage hook (default {DEFAULT_REGEX})")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.team_repo)
    if not os.path.isdir(target):
        print(f"FAIL  not a folder: {args.team_repo}")
        return 2
    if os.path.normcase(target) == os.path.normcase(KIT_REPO):
        print("FAIL  target is the kit repo itself; run this from your team repo:  python <kit>/scripts/export_pack.py .")
        return 2
    regex = args.ticket_regex
    if regex is None:
        try:
            regex = input(f"Ticket regex ของทีม [{DEFAULT_REGEX}]: ").strip()
        except EOFError:
            regex = ""
        regex = regex or DEFAULT_REGEX
    try:
        re.compile(regex)
    except re.error as exc:
        print(f"FAIL  ticket regex does not compile: {exc}")
        return 2

    for rel in FILES:
        src = os.path.join(KIT_REPO, rel)
        dst = os.path.join(target, rel)
        if not os.path.isfile(src):
            print(f"WARN  missing in kit: {rel}")
            continue
        if os.path.exists(dst):
            print(f"SKIP exists  {rel}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"COPIED  {rel}")
    link = os.path.join(target, ".claude", "linkage.json")
    if os.path.exists(link):
        print("SKIP exists  .claude/linkage.json")
    else:
        os.makedirs(os.path.dirname(link), exist_ok=True)
        with open(link, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"ticket_pattern": regex}, indent=2, ensure_ascii=False) + "\n")
        print(f"WROTE  .claude/linkage.json  ticket_pattern={regex}")
    print("next:")
    print("  python scripts/hooks.py enable linkage")
    print("  git diff .claude/settings.json")
    print("  python scripts/hooks.py test linkage")
    print("  python scripts/audit.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
