#!/usr/bin/env python
"""PreToolUse hook (Edit | Write | NotebookEdit): block edits to protected files.

Protected paths come from .claude/protected_paths.json ({"protected": [...]}); an entry
ending in "/" is a folder prefix. Extra lists in .claude/protected_paths.*.json (for
example protected_paths.d2.json on Day 2) are added when present.
The target path is made repo-relative (backslash -> slash, case-insensitive on Windows).

Exit 0 = allow, exit 2 = block (stderr goes back to Claude). Fail-closed: input it
cannot parse is blocked. Registered as:  python "<hook>" || exit 2
Shipped on Day 1 but not registered (python scripts/hooks.py enable protect).
Standalone: stdlib only, no imports from other kit files.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOOK = "protect"
TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
DEFAULT_PROTECTED = ["tests/test_rules.py", "tests/test_service.py", ".claude/settings.json",
                     ".claude/settings.local.json", ".claude/hooks/", ".claude/protected_paths.json"]
WINDOWS = os.name == "nt"


def log(project: str, tool: str, decision: str, reason: str) -> None:
    try:
        folder = os.path.join(project, "artifacts")
        os.makedirs(folder, exist_ok=True)
        ignore = os.path.join(folder, ".gitignore")
        if not os.path.exists(ignore):  # self-ignoring log folder: never swept into a team repo commit
            with open(ignore, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("*\n")
        rec = {"hook": HOOK, "tool": tool, "decision": decision, "reason": reason,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        with open(os.path.join(folder, "hook_decisions.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def norm(path: str) -> str:
    p = path.replace("\\", "/")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)  # Git Bash style /c/work/...
    if m and WINDOWS:
        p = f"{m.group(1)}:/{m.group(2)}"
    p = os.path.normpath(p).replace("\\", "/")
    return p.lower() if WINDOWS else p


def load_protected(project: str) -> list[str]:
    files = [os.path.join(project, ".claude", "protected_paths.json")]
    files += sorted(glob.glob(os.path.join(project, ".claude", "protected_paths.*.json")))
    items: list[str] = []
    found = False
    for f in files:
        try:
            with open(f, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
            found = True
            items += [str(x) for x in data.get("protected", [])]
        except FileNotFoundError:
            continue
        except Exception:
            raise ValueError(f"cannot read {os.path.basename(f)}")
    return items if found else list(DEFAULT_PROTECTED)


def block(project: str, tool: str, reason: str, line: str) -> int:
    log(project, tool, "block", reason)
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
    return 2


def main() -> int:
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception:
        return block(project or os.getcwd(), "?", "unparseable input",
                     "Blocked by protect_files: cannot parse hook input (fail-closed)")
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
    project = project or cwd
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    if tool not in TOOLS or not isinstance(tool_input, dict):
        return 0
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(target, str) or not target.strip():
        return 0
    try:
        protected = load_protected(project)
    except ValueError as exc:
        return block(project, tool, str(exc), f"Blocked by protect_files: {exc} (fail-closed)")

    t = target.replace("\\", "/")
    if not (os.path.isabs(t) or re.match(r"^[a-zA-Z]:/", t) or re.match(r"^/[a-zA-Z]/", t)):
        t = os.path.join(cwd, t)
    full, root = norm(t), norm(project).rstrip("/")
    if full == root or not full.startswith(root + "/"):
        log(project, tool, "allow", "outside project")
        return 0
    rel = full[len(root) + 1:]
    shown = os.path.normpath(t).replace("\\", "/")[-len(rel):]  # original case for the message
    for entry in protected:
        e = entry.replace("\\", "/")
        if e.startswith("./"):
            e = e[2:]
        e = e.lower() if WINDOWS else e
        hit = rel.startswith(e) if e.endswith("/") else rel == e
        if hit:
            return block(project, tool, f"protected {entry}",
                         f"Blocked by protect_files: {shown} is protected. ห้ามแก้ test เดิม: แก้โค้ดแทน "
                         f"หรือเขียน artifacts/escalation.md (tests change only via QA with Approved-by).")
    log(project, tool, "allow", rel)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"Blocked by protect_files: internal error ({type(exc).__name__}) (fail-closed)\n")
        sys.exit(2)
