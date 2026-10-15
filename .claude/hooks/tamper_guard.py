#!/usr/bin/env python
"""PreToolUse hook (Bash | PowerShell | Monitor): block shell commands that write protected files.

The protect hook only sees Edit/Write/NotebookEdit. A shell command can still overwrite a
protected file (redirect, tee, sed -i, python write_text/open(...,'w'), rm/mv/cp, PowerShell
Set-Content/Out-File/Remove-Item, git checkout -- / git rm). This hook blocks a command when
  (a) it mentions a protected path (basename match, case-insensitive; also tests/test_rules,
      settings.json, .claude/hooks)  AND  (b) it contains a write token,
or when it tries to switch the guards off (disableAllHooks, protect_tests.sh off, hooks.py disable).
Read-only commands (cat, grep, git diff, python -m pytest tests/test_rules.py) pass.

Protected paths come from .claude/protected_paths.json (+ protected_paths.*.json) like protect_files.py.
Exit 0 = allow, exit 2 = block (stderr goes back to Claude). Fail-closed: input it cannot parse is
blocked. Registered as:  python "<hook>" || exit 2   (Lab 4 blue team: python scripts/hooks.py enable tamper)
Every decision is appended to artifacts/hook_decisions.jsonl ("hook": "tamper").
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

HOOK = "tamper"
TOOLS = {"Bash", "PowerShell", "Monitor"}
DEFAULT_PROTECTED = ["tests/test_rules.py", "tests/test_service.py", ".claude/settings.json",
                     ".claude/settings.local.json", ".claude/hooks/", ".claude/protected_paths.json"]
EXTRA_TOKENS = ["tests/test_rules", "settings.json", ".claude/hooks"]
WINDOWS = os.name == "nt"

WRITE_TOKENS: list[tuple[str, re.Pattern]] = [
    (">", re.compile(r"(?<![0-9<>-])>>?(?!&)")),                                     # > or >>, not 2>, >&, ->
    ("tee", re.compile(r"(^|[\s;&|(`])tee(\s|$)")),
    ("sed -i", re.compile(r"(^|[\s;&|(`])sed\s+(?:-\S+\s+)*(?:-[a-zA-Z]*i|--in-place)\b")),
    ("write_text", re.compile(r"\bwrite_(?:text|bytes)\s*\(")),
    ("open(...,'w')", re.compile(r"\bopen\s*\([^)]*['\"](?:[wax]\+?b?|[wax]b\+?|r\+b?|rb\+)['\"]")),
    ("rm/del/mv/cp", re.compile(r"(^|[\s;&|(`])(?:rm|del|mv|cp|rmdir|unlink|truncate)\s")),
    ("PowerShell write cmdlet", re.compile(r"\b(?:Set-Content|Out-File|Remove-Item|Move-Item|Copy-Item|Add-Content|"
                                           r"New-Item|Clear-Content|Rename-Item)\b", re.IGNORECASE)),
    ("git checkout --", re.compile(r"\bgit\s+(?:-[Cc]\s+\S+\s+)?(?:checkout|restore)\b")),
    ("git rm", re.compile(r"\bgit\s+(?:-[Cc]\s+\S+\s+)?(?:rm|mv)\b")),
]
KILL_SWITCHES: list[tuple[str, re.Pattern]] = [
    ("disableAllHooks", re.compile(r"disableAllHooks", re.IGNORECASE)),
    ("protect_tests.sh off", re.compile(r"protect_tests\.sh\s+off")),
    ("hooks.py disable", re.compile(r"hooks\.py\s+disable\b")),
]


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


def win_path(path: str) -> str:
    if WINDOWS and path:
        m = re.match(r"^/([a-zA-Z])/(.*)$", path.replace("\\", "/"))
        if m:
            return f"{m.group(1).upper()}:/{m.group(2)}"
    return path


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


def mentioned_path(command: str, protected: list[str]) -> str | None:
    """The protected entry (or extra token) the command mentions, if any."""
    low = command.replace("\\", "/").lower()
    for entry in protected:
        e = entry.replace("\\", "/").strip().lower()
        if e.startswith("./"):
            e = e[2:]
        token = e.rstrip("/") if e.endswith("/") else e.rsplit("/", 1)[-1]  # folder -> its path, file -> basename
        if token and token in low:
            return entry
    for token in EXTRA_TOKENS:
        if token.lower() in low:
            return token
    return None


def write_token(command: str) -> str | None:
    for name, pat in WRITE_TOKENS:
        if pat.search(command):
            return name
    return None


def kill_switch(command: str) -> str | None:
    for name, pat in KILL_SWITCHES:
        if pat.search(command):
            return name
    return None


def block(project: str, tool: str, reason: str, line: str) -> int:
    log(project, tool, "block", reason)
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
    return 2


def main() -> int:
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    project = win_path(os.environ.get("CLAUDE_PROJECT_DIR") or "")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception:
        return block(project or os.getcwd(), "?", "unparseable input",
                     "Blocked by tamper_guard: cannot parse hook input (fail-closed)")
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd").strip() else os.getcwd()
    project = project or win_path(cwd)
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if tool not in TOOLS or not isinstance(command, str) or not command.strip():
        return 0  # Monitor without a command, other tools: nothing to inspect

    switch = kill_switch(command)
    if switch:
        return block(project, tool, f"kill switch {switch}",
                     f"Blocked by tamper_guard: คำสั่งนี้ปิด hook ({switch}) การปิดหรือแก้ guard ต้องให้คนทำเองใน terminal 2 "
                     f"และ commit พร้อม Approved-by")
    try:
        protected = load_protected(project)
    except ValueError as exc:
        return block(project, tool, str(exc), f"Blocked by tamper_guard: {exc} (fail-closed)")
    path = mentioned_path(command, protected)
    if path is None:
        log(project, tool, "allow", "no protected path")
        return 0
    token = write_token(command)
    if token is None:
        log(project, tool, "allow", f"read-only ({path})")
        return 0
    return block(project, tool, f"write {token} -> {path}",
                 f"Blocked by tamper_guard: คำสั่งนี้เขียนทับไฟล์ที่ protect ({path}) ใช้ Edit/Write ตามปกติ หรือแก้โค้ดแทน")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # any crash blocks (fail-closed)
        sys.stderr.write(f"Blocked by tamper_guard: internal error ({type(exc).__name__}) (fail-closed)\n")
        sys.exit(2)
