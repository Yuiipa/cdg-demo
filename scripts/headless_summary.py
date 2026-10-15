#!/usr/bin/env python
"""Summarise a `claude -p ... --output-format json` result file (Day 2, Lab 2 headless run).

Usage (from the repo root):
    python scripts/headless_summary.py artifacts/review_headless.json
    python scripts/headless_summary.py artifacts/review_headless.json --full

Prints one HEADLESS line (subtype, turns, cost, duration, permission denials), then
"RESULT (first 20 lines)" and the first 20 lines of the `result` text (--full prints all).
Accepts UTF-8 and UTF-16 files (PowerShell `>` writes UTF-16; Git Bash writes UTF-8).
Exit 0 = OK, 1 = file missing / not JSON / is_error true (prints "HEADLESS  FAIL: ...").
"""
from __future__ import annotations

import json
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HEAD_LINES = 20


def read_text(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if len(raw) >= 2 and raw[0] != 0 and raw[1] == 0:  # UTF-16 LE without BOM
        return raw.decode("utf-16-le", "replace")
    return raw.decode("utf-8-sig", "replace")


def load_result(path: str) -> dict:
    data = json.loads(read_text(path))
    if isinstance(data, list):  # stream-json style: the result message is the last one
        results = [m for m in data if isinstance(m, dict) and m.get("type") == "result"]
        if not results:
            raise ValueError("no message of type 'result' in the JSON array")
        data = results[-1]
    if not isinstance(data, dict):
        raise ValueError("top level is not a JSON object")
    return data


def fail(msg: str) -> int:
    print(f"HEADLESS  FAIL: {msg}")
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    full = "--full" in argv
    argv = [a for a in argv if a != "--full"]
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("usage: python scripts/headless_summary.py <result.json> [--full]")
        return 1
    path = argv[0]
    if not os.path.isfile(path):
        return fail(f"{path.replace(chr(92), '/')} not found (did the claude -p command run? Git Bash, not PowerShell)")
    if os.path.getsize(path) == 0:
        return fail(f"{path.replace(chr(92), '/')} is empty (claude -p printed nothing; check the command and your login)")
    try:
        data = load_result(path)
    except ValueError as exc:
        return fail(f"not valid JSON ({exc}); use --output-format json and redirect in Git Bash")

    subtype = data.get("subtype") or "?"
    turns = data.get("num_turns")
    cost = data.get("total_cost_usd")
    duration_ms = data.get("duration_ms")
    denials = data.get("permission_denials") or []
    cost_s = f"${cost:.2f}" if isinstance(cost, (int, float)) else "?"
    dur_s = f"{round(duration_ms / 1000)} s" if isinstance(duration_ms, (int, float)) else "?"
    turns_s = turns if isinstance(turns, int) else "?"
    print(f"HEADLESS  subtype: {subtype} · turns: {turns_s} · cost: {cost_s} · duration: {dur_s} · denials: {len(denials)}")
    for d in denials[:5]:
        if isinstance(d, dict):
            print(f"          denied: {d.get('tool_name', '?')} {json.dumps(d.get('tool_input', {}), ensure_ascii=False)[:120]}")

    if data.get("is_error"):
        result = data.get("result")
        print(f"          {str(result)[:300]}" if result else "")
        return fail(f"is_error true (subtype {subtype})")

    result = data.get("result")
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, indent=2) if result is not None else ""
    lines = result.splitlines()
    if full:
        print(f"RESULT ({len(lines)} lines)")
        shown = lines
    else:
        print(f"RESULT (first {HEAD_LINES} lines)")
        shown = lines[:HEAD_LINES]
    for line in shown:
        print(line)
    if not full and len(lines) > HEAD_LINES:
        print(f"… ({len(lines) - HEAD_LINES} more lines: --full)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
