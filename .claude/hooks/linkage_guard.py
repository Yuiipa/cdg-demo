#!/usr/bin/env python
"""PreToolUse hook (Bash | PowerShell | Monitor): every git commit must carry a ticket.

A command that runs `git commit` must contain "Refs: <ticket>" (in --trailer, -m, a
heredoc message, or the -F/--file message file). The ticket pattern comes from
.claude/linkage.json ({"ticket_pattern": "..."}), default (BOOK|CHG|PLAT|SPEC-BK)-\\d+.
`git commit --amend --no-edit` is checked against the last commit message.

Exit 0 = allow, exit 2 = block (stderr goes back to Claude). Fail-closed: input it
cannot parse is blocked. Registered as:  python "<hook>" || exit 2
Every decision is appended (best effort) to artifacts/hook_decisions.jsonl.
Standalone: stdlib only, no imports from other kit files.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOOK = "linkage"
TOOLS = {"Bash", "PowerShell", "Monitor"}
DEFAULT_PATTERN = r"(BOOK|CHG|PLAT|SPEC-BK)-\d+"
COMMIT_RE = re.compile(r"(^|[;&|(\s])git(\s+-[Cc]\s+\S+)*\s+commit\b")
BLOCK_LINE_1 = 'Blocked by linkage_guard: commit must carry Refs: <ticket>; add --trailer "Refs: BOOK-142"'
BLOCK_LINE_2 = "(git commit ต้องมี trailer Refs: ตาม .claude/linkage.json ใช้ ticket ของงานนี้ แล้ว commit ใหม่)"


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
        pass  # logging never changes the decision


def load_pattern(project: str) -> str:
    try:
        with open(os.path.join(project, ".claude", "linkage.json"), "r", encoding="utf-8-sig") as fh:
            pat = json.load(fh).get("ticket_pattern") or DEFAULT_PATTERN
        re.compile(pat)
        return pat
    except Exception:
        return DEFAULT_PATTERN


def message_files(command: str) -> list[str]:
    """Paths given with -F / --file / --file=."""
    try:
        tokens = shlex.split(command, posix=False)  # keep Windows backslashes
    except ValueError:
        tokens = command.split()
    tokens = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t for t in tokens]
    out = []
    for i, tok in enumerate(tokens):
        if tok in ("-F", "--file") and i + 1 < len(tokens):
            out.append(tokens[i + 1])
        elif tok.startswith("--file="):
            out.append(tok[len("--file="):])
        elif tok.startswith("-F") and len(tok) > 2 and not tok.startswith("--"):
            out.append(tok[2:])
    return out


def last_commit_message(project: str) -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%B"], cwd=project, capture_output=True, timeout=10)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def block(project: str, tool: str, reason: str, lines: list[str]) -> int:
    log(project, tool, "block", reason)
    sys.stderr.write("\n".join(lines) + "\n")
    sys.stderr.flush()
    return 2


def main() -> int:
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception:
        return block(project, "?", "unparseable input",
                     ["Blocked by linkage_guard: cannot parse hook input (fail-closed)"])
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(payload.get("cwd"), str):
        project = payload["cwd"]
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if tool not in TOOLS or not isinstance(command, str) or not command.strip():
        return 0
    if not COMMIT_RE.search(command):
        return 0

    pattern = load_pattern(project)
    refs_re = re.compile(r"Refs\s*[:=]\s*[\"']?\s*(?:" + pattern + r")")
    texts = [command]
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else project
    for f in message_files(command):
        if f == "-":
            continue
        path = f if os.path.isabs(f) else os.path.join(cwd, f)
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                texts.append(fh.read())
        except OSError:
            pass
    if re.search(r"--amend\b", command) and re.search(r"--no-edit\b", command):
        texts.append(last_commit_message(cwd))
    if any(refs_re.search(t) for t in texts):
        log(project, tool, "allow", "commit has Refs")
        return 0
    line1 = BLOCK_LINE_1
    if not refs_re.search("Refs: BOOK-142"):  # team pattern (Track R): do not suggest a kit ticket
        line1 = line1.replace('"Refs: BOOK-142"', '"Refs: <ticket>"')
    return block(project, tool, "git commit without Refs: <ticket>", [line1, BLOCK_LINE_2])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # any crash blocks (fail-closed)
        sys.stderr.write(f"Blocked by linkage_guard: internal error ({type(exc).__name__}) (fail-closed)\n")
        sys.exit(2)
