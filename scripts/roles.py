#!/usr/bin/env python
"""Reveal a lab card from ../cdg-acceptance into the repo, at the moment the lab needs it.

Usage (from the repo root):
    python scripts/roles.py list
    python scripts/roles.py reveal po        # D1-L3: PO decision card -> intent/sources/recurring/po_decisions.md
    python scripts/roles.py reveal ticket    # D1-L2 MCP fallback: BOOK-142 -> intent/sources/recurring/BOOK-142.md

The originator persona card is never copied into the repo (read it on paper, or
code ../cdg-acceptance/roles/persona_originator.md).
Exit 0 = revealed or already present, 2 = ../cdg-acceptance or the card not found.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CARDS = {
    "po": ("roles/po_decisions.md", "intent/sources/recurring/po_decisions.md", "D1-L3 PO decision card"),
    "ticket": ("tickets/BOOK-142.md", "intent/sources/recurring/BOOK-142.md", "D1-L2 ticket BOOK-142 (MCP fallback)"),
}


def acceptance_dir() -> str:
    env = os.environ.get("CDG_ACCEPTANCE_DIR")
    return os.path.abspath(env) if env else os.path.abspath(os.path.join(REPO, "..", "cdg-acceptance"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="roles.py", description="Reveal a lab card (PO decisions, ticket file) into the repo.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="show what can be revealed")
    p = sub.add_parser("reveal", help="copy a card into intent/sources/recurring/")
    p.add_argument("what", choices=sorted(CARDS))
    args = ap.parse_args(argv)

    acc = acceptance_dir()
    if args.cmd == "list":
        for key, (src, dst, desc) in CARDS.items():
            have = "available" if os.path.isfile(os.path.join(acc, src)) else "missing"
            there = " (already in repo)" if os.path.isfile(os.path.join(REPO, dst)) else ""
            print(f"{key:<7} {desc:<40} -> {dst}  [{have}]{there}")
        return 0
    if args.cmd != "reveal":
        ap.print_help()
        return 2

    src_rel, dst_rel, _ = CARDS[args.what]
    src = os.path.join(acc, src_rel)
    dst = os.path.join(REPO, dst_rel)
    if os.path.isfile(dst):
        print(f"INFO  already present: {dst_rel}")
        return 0
    if not os.path.isdir(acc):
        print("FAIL  ../cdg-acceptance not found (keep the kit folders together)")
        return 2
    if not os.path.isfile(src):
        print(f"FAIL  card not found: ../cdg-acceptance/{src_rel}")
        return 2
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"REVEALED {args.what} -> {dst_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
