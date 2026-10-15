#!/usr/bin/env python
"""Show or reset the state of the Stop-hook test loop (Day 2 Lab 1).

Usage (from the repo root):
    python scripts/loop.py status
    python scripts/loop.py reset

status prints exactly one line:
    LOOP  rounds: <n>/3 · last pytest: PASS (27 passed)|FAIL (2 failed, 25 passed)|none · escalation: none|artifacts/escalation.md · protected tests: unchanged|CHANGED (<files>)
  rounds  = artifacts/.round (the hook deletes it when pytest passes; then the highest artifacts/round_<n>.txt counts)
  last pytest = summary line of artifacts/last_pytest.txt (written by the Stop hook)
  protected tests = tests/test_rules.py, tests/test_service.py vs `git merge-base main HEAD` (same check as the hook)
reset moves artifacts/round_*.txt, last_pytest.txt and escalation.md to artifacts/archive/<YYYYmmdd-HHMMSS>/ and
deletes artifacts/.round, then prints:
    LOOP  reset: rounds 0 · artifacts/escalation.md: none|archived
Exit 0 always (2 if this is not a git repository). Standalone: stdlib only.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ARTIFACTS = os.path.join(REPO, "artifacts")
MAX_ROUNDS = 3
DEFAULT_PROTECTED_TESTS = ["tests/test_rules.py", "tests/test_service.py"]


def git(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return 127, ""
    return p.returncode, p.stdout.decode("utf-8", "replace")


def protected_tests() -> list[str]:
    items: list[str] = []
    try:
        with open(os.path.join(REPO, ".claude", "protected_paths.json"), "r", encoding="utf-8-sig") as fh:
            for entry in json.load(fh).get("protected", []):
                e = str(entry).replace("\\", "/")
                if e.startswith("./"):
                    e = e[2:]
                if e.startswith("tests/") and not e.endswith("/"):
                    items.append(e)
    except Exception:
        items = []
    return items or list(DEFAULT_PROTECTED_TESTS)


def merge_base() -> str:
    code, out = git(["merge-base", "main", "HEAD"])
    if code == 0 and out.strip():
        return out.strip()
    code, out = git(["rev-parse", "HEAD"])
    return out.strip() if code == 0 and out.strip() else "HEAD"


def protected_changed() -> list[str]:
    files = protected_tests()
    base = merge_base()
    code, _ = git(["diff", "--quiet", base, "--", *files])
    if code != 1:
        return []
    code, out = git(["diff", "--name-only", base, "--", *files])
    changed = [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()] if code == 0 else []
    return changed or files


def rounds() -> int:
    try:
        with open(os.path.join(ARTIFACTS, ".round"), "r", encoding="utf-8-sig") as fh:
            return max(0, int(fh.read().strip() or "0"))
    except Exception:
        pass
    best = 0
    for f in glob.glob(os.path.join(ARTIFACTS, "round_*.txt")):
        m = re.match(r"round_(\d+)\.txt$", os.path.basename(f))
        if m:
            best = max(best, int(m.group(1)))
    return best


def last_pytest() -> str:
    path = os.path.join(ARTIFACTS, "last_pytest.txt")
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return "none"
    line = ""
    for ln in reversed(lines):
        if re.search(r"\d+ (passed|failed|error)", ln) or "no tests ran" in ln:
            line = ln.strip(" =")
            break
    if not line:
        return "FAIL (no summary line)"
    parts = []
    failed = errors = 0
    for key in ("failed", "passed", "error"):
        m = re.search(r"(\d+) " + key + r"s?\b", line)
        if m:
            n = int(m.group(1))
            parts.append(f"{n} {key}")
            if key == "failed":
                failed = n
            elif key == "error":
                errors = n
    status = "FAIL" if (failed or errors or "no tests ran" in line) else "PASS"
    return f"{status} ({', '.join(parts) if parts else line})"


def ensure_artifacts() -> None:
    os.makedirs(ARTIFACTS, exist_ok=True)
    ignore = os.path.join(ARTIFACTS, ".gitignore")
    if not os.path.exists(ignore):  # self-ignoring folder, same as the hooks
        with open(ignore, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("*\n")


def cmd_status() -> int:
    esc = os.path.join(ARTIFACTS, "escalation.md")
    changed = protected_changed()
    print(f"LOOP  rounds: {rounds()}/{MAX_ROUNDS} · last pytest: {last_pytest()} · "
          f"escalation: {'artifacts/escalation.md' if os.path.exists(esc) else 'none'} · "
          f"protected tests: {'CHANGED (' + ', '.join(changed) + ')' if changed else 'unchanged'}")
    return 0


def cmd_reset() -> int:
    ensure_artifacts()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archive = os.path.join(ARTIFACTS, "archive", stamp)
    to_move = sorted(glob.glob(os.path.join(ARTIFACTS, "round_*.txt")))
    for name in ("last_pytest.txt", "escalation.md"):
        p = os.path.join(ARTIFACTS, name)
        if os.path.isfile(p):
            to_move.append(p)
    escalated = any(os.path.basename(p) == "escalation.md" for p in to_move)
    if to_move:
        os.makedirs(archive, exist_ok=True)
        for p in to_move:
            try:
                shutil.move(p, os.path.join(archive, os.path.basename(p)))
            except OSError:
                pass
    try:
        os.remove(os.path.join(ARTIFACTS, ".round"))
    except OSError:
        pass
    print(f"LOOP  reset: rounds 0 · artifacts/escalation.md: {'archived' if escalated else 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "status"
    if cmd not in ("status", "reset"):
        print(__doc__.strip().splitlines()[0])
        print("usage: python scripts/loop.py status | reset")
        return 0
    code, _ = git(["rev-parse", "--git-dir"])
    if code != 0:
        print("LOOP  FAIL: not a git repository (run from the repo root)")
        return 2
    return cmd_status() if cmd == "status" else cmd_reset()


if __name__ == "__main__":
    sys.exit(main())
