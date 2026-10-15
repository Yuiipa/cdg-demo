#!/usr/bin/env python
"""Readiness check for Day 2 (run at 08:30 after apply_day2.py + commit, from the repo root).

Usage:
    source .venv/Scripts/activate
    python scripts/day2_check.py [--skip-claude]

PowerShell: .\\.venv\\Scripts\\python.exe scripts\\day2_check.py
Rows: PASS / WARN / FAIL / INFO (same style as precheck.py). Last line: "DAY2 CHECK: PASS (n WARN)"
(exit 0) or "DAY2 CHECK: FAIL (n)" (exit 1). WARN rows never block class.
--skip-claude skips the `claude mcp get internal-tools` row.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WINDOWS = os.name == "nt"
PYTEST_MIN = 22
APPLY_HINT = "run apply_day2.py again: python ../../cdg-kit-v3-day2/apply_day2.py"
FALLBACK = "Lab 3 fallback: python scripts/mcp_tools.py"

# every file the Day-2 overlay adds to the learner repo, plus the two files next to it
DAY2_FILES = [
    "intent/fr6-small-room-limit/intent.md",
    "intent/fr6-small-room-limit/spec.md",
    "prompts/mc_task.md",
    "prompts/loop_task.md",
    "prompts/review_request.md",
    "prompts/review_headless.md",
    "prompts/mcp_tool_plan.md",
    "prompts/red_team.md",
    ".claude/hooks/stop_guard.py",
    ".claude/hooks/tamper_guard.py",
    ".claude/hooks/snippets/stop.json",
    ".claude/hooks/snippets/tamper.json",
    ".claude/agents/reviewer.md",
    "scripts/hooks.py",
    "scripts/loop.py",
    "scripts/mcp_tools.py",
    "scripts/headless_summary.py",
    "scripts/day2_check.py",
    "mcp_server/internal_tools/data.py",
    "docs/templates/MC_CARD_D2.md",
    "docs/templates/LOOP_CANVAS.md",
    "docs/templates/REVIEW.md",
    "docs/templates/RED_BLUE_SCORE.md",
    "docs/templates/ACTION_PLAN_30D.md",
    "../cdg-acceptance/scenarios/fr6.py",
    "../LABS_D2.md",
]
# files that apply_day2.py REPLACES: a marker that only the Day-2 version contains
REPLACED_MARKERS = {
    "scripts/hooks.py": "tamper",
    "mcp_server/internal_tools/data.py": "INCIDENTS",
}


class Rows:
    def __init__(self) -> None:
        self.fails = 0
        self.warns = 0

    def row(self, status: str, label: str, hint: str = "") -> None:
        if status == "FAIL":
            self.fails += 1
        elif status == "WARN":
            self.warns += 1
        print(f"{status:<4}  {label}")
        if hint and status in ("FAIL", "WARN", "INFO"):
            for line in hint.splitlines():
                print(f"      {line}")


def run(cmd: list[str], timeout: int = 60, cwd: str | None = None, env: dict | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd or REPO, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env=env)
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except OSError as exc:
        return 127, str(exc)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def child_env() -> dict:
    return dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")


def shim(path: str) -> list[str]:
    return ["cmd", "/c", path] if path.lower().endswith((".cmd", ".bat")) else [path]


def acceptance_dir() -> str:
    env = os.environ.get("CDG_ACCEPTANCE_DIR")
    return os.path.abspath(env) if env else os.path.abspath(os.path.join(REPO, "..", "cdg-acceptance"))


def resolve(rel: str) -> str:
    if rel.startswith("../cdg-acceptance/"):
        return os.path.join(acceptance_dir(), rel[len("../cdg-acceptance/"):])
    return os.path.normpath(os.path.join(REPO, rel))


# ------------------------------------------------------------------ rows
def row_git(r: Rows) -> None:
    code, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=20)
    if code != 0:
        r.row("FAIL", "git: not a git repository (or git missing)", "open C:\\work\\cdg-kit-v3\\cdg-claude-code-demo in Git Bash")
        return
    branch = branch.strip() or "?"
    _, status = run(["git", "status", "--porcelain"], timeout=20)
    dirty = [l for l in status.splitlines() if l.strip()]
    state = "clean" if not dirty else f"{len(dirty)} uncommitted change(s)"
    label = f"git: branch {branch} · {state}"
    if dirty:
        r.row("WARN", label, 'commit the Day-2 files first: git add -A && git commit -m "chore(kit): day 2 files" --trailer "Refs: PLAT-7"')
    elif branch != "main":
        r.row("WARN", label, "expected main at 08:30 (fine later in the day): git switch main")
    else:
        r.row("PASS", label)


def row_files(r: Rows) -> None:
    missing = [f for f in DAY2_FILES if not os.path.isfile(resolve(f))]
    total = len(DAY2_FILES)
    present = total - len(missing)
    if missing:
        shown = ", ".join(missing[:3]) + (" …" if len(missing) > 3 else "")
        r.row("FAIL", f"day 2 files: {present}/{total} present (missing: {shown})", APPLY_HINT)
        return
    stale = []
    for rel, marker in REPLACED_MARKERS.items():
        try:
            with open(resolve(rel), "r", encoding="utf-8-sig", errors="replace") as fh:
                if marker not in fh.read():
                    stale.append(rel)
        except OSError:
            stale.append(rel)
    if stale:
        r.row("WARN", f"day 2 files: {present}/{total} present · still the Day-1 version: {', '.join(stale)}", APPLY_HINT)
    else:
        r.row("PASS", f"day 2 files: {present}/{total} present")


def pytest_counts(out: str) -> tuple[int, int]:
    for line in reversed(out.splitlines()):
        if re.search(r"\b(passed|failed|errors?|no tests ran)\b", line) and re.search(r"\bin [\d.]+s", line):
            m = re.search(r"(\d+) passed", line)
            failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|errors?)\b", line))
            return (int(m.group(1)) if m else 0), failed
    return 0, -1


def row_pytest(r: Rows) -> None:
    code, out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], timeout=300, env=child_env())
    passed, failed = pytest_counts(out)
    fix = "python -m pip install -r requirements-dev.txt   (offline: --no-index --find-links ../wheels)"
    if "No module named pytest" in out:
        r.row("FAIL", "pytest: not installed (is .venv active?)", fix)
    elif failed == 0 and passed >= PYTEST_MIN:
        r.row("PASS", f"pytest: {passed} passed")
    elif failed == 0 and passed > 0:
        r.row("FAIL", f"pytest: {passed} passed (expected >= {PYTEST_MIN} at d1-end)", "python scripts/savepoint.py catchup d1-end  then apply_day2.py again")
    elif failed < 0:
        tail = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
        r.row("FAIL", f"pytest: no result ({tail[:100]})", fix)
    else:
        r.row("FAIL", f"pytest: {passed} passed, {failed} failed", "run python -m pytest and show the TA")


def row_acceptance(r: Rows) -> None:
    check_py = os.path.join(acceptance_dir(), "check.py")
    label = "FR-6 acceptance runs"
    if not os.path.isfile(check_py):
        r.row("FAIL", f"{label}: ../cdg-acceptance/check.py not found", "keep the kit folders together (cdg-kit-v3/cdg-acceptance next to the repo)")
        return
    code, out = run([sys.executable, check_py, "FR-6", "--repo", REPO], timeout=120, env=child_env())
    m = re.search(r"ACCEPTANCE (\d+)/(\d+)", out)
    if m:
        got, tot = int(m.group(1)), int(m.group(2))
        note = " (expected before Lab 1)" if got < tot else ""
        r.row("PASS", f"{label}: ACCEPTANCE {got}/{tot}{note}")
    elif "unknown suite" in out:
        r.row("FAIL", f"{label}: suite FR-6 missing (../cdg-acceptance/scenarios/fr6.py)", APPLY_HINT)
    else:
        tail = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
        r.row("FAIL", f"{label}: no ACCEPTANCE line ({tail[:100]})", "python ../cdg-acceptance/check.py FR-6  and show the TA")


def hook_names() -> tuple[list[str], list[str], str | None]:
    """(enabled, available, error) read from settings.json + .claude/hooks/snippets/*.json."""
    path = os.path.join(REPO, ".claude", "settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            settings = json.load(fh)
    except OSError:
        settings, err = {}, "settings.json missing"
    except ValueError as exc:
        return [], [], f"settings.json not valid JSON ({exc})"
    else:
        err = None
    commands = set()
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries or []:
            for h in entry.get("hooks", []) or []:
                commands.add(h.get("command"))
    available, enabled = [], []
    snip_dir = os.path.join(REPO, ".claude", "hooks", "snippets")
    if os.path.isdir(snip_dir):
        for fn in sorted(os.listdir(snip_dir)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(snip_dir, fn), "r", encoding="utf-8-sig") as fh:
                    snip = json.load(fh)
            except (OSError, ValueError):
                continue
            name = snip.get("name", fn[:-5])
            available.append(name)
            if snip.get("hook", {}).get("command") in commands:
                enabled.append(name)
    return enabled, available, err


def row_hooks(r: Rows) -> None:
    enabled, available, err = hook_names()
    if err and "not valid JSON" in err:
        r.row("FAIL", f"hooks: {err}", "fix .claude/settings.json (git diff .claude/settings.json) or ask the TA")
        return
    r.row("INFO", f"hooks enabled: {', '.join(enabled) if enabled else '(none)'}  (available: {', '.join(available) if available else '(none)'})")


def row_mcp_tools(r: Rows) -> None:
    label = "MCP internal-tools"
    script = os.path.join(HERE, "mcp_tools.py")
    if not os.path.isfile(script):
        r.row("FAIL", f"{label}: scripts/mcp_tools.py missing", APPLY_HINT)
        return
    code, out = run([sys.executable, script, "list"], timeout=120, env=child_env())
    m = re.search(r"MCP \S+ · (\d+) tools \(mcp ([^)]+)\)", out)
    if m and code == 0:
        r.row("PASS", f"{label}: {m.group(1)} tools (mcp {m.group(2)})")
    elif m and "WARN  day2_tools" in out:
        r.row("WARN", f"{label}: {m.group(1)} tools (mcp {m.group(2)}) · day2_tools import failed", "python scripts/mcp_tools.py list --trace")
    else:
        tail = next((l for l in out.splitlines() if l.startswith(("FAIL", "WARN"))), out.strip().splitlines()[-1] if out.strip() else f"exit {code}")
        r.row("FAIL", f"{label}: server cannot import ({tail[:110]})", "python -m pip install -r requirements-mcp.txt   then python scripts/mcp_tools.py list --trace")


def row_claude_mcp(r: Rows) -> None:
    label = "claude mcp get internal-tools"
    path = shutil.which("claude")
    if not path:
        r.row("WARN", f"{label}: claude not found ({FALLBACK})", "install Claude Code / open a new terminal; python scripts/setup_mcp.py registers the server")
        return
    code, out = run(shim(path) + ["mcp", "get", "internal-tools"], timeout=20)
    if "Connected" in out and "Failed" not in out:
        r.row("PASS", f"{label}: Connected")
    elif code == 124:
        r.row("WARN", f"{label}: timeout 20 s ({FALLBACK})", "try again: claude mcp get internal-tools")
    elif "No MCP server" in out or code != 0:
        r.row("WARN", f"{label}: not registered ({FALLBACK})", "register: python scripts/setup_mcp.py   then /exit and relaunch Claude")
    else:
        status = next((l.strip() for l in out.splitlines() if "Status" in l), out.strip().splitlines()[-1] if out.strip() else "?")
        r.row("WARN", f"{label}: {status[:80]} ({FALLBACK})", "python scripts/setup_mcp.py   then /exit and relaunch Claude")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="day2_check.py", description="Day-2 readiness check (08:30, after apply_day2.py).")
    ap.add_argument("--skip-claude", action="store_true", help="skip the claude mcp get row")
    args = ap.parse_args(argv)

    r = Rows()
    row_git(r)
    row_files(r)
    row_pytest(r)
    row_acceptance(r)
    row_hooks(r)
    row_mcp_tools(r)
    if not args.skip_claude:
        row_claude_mcp(r)
    if r.fails:
        print(f"DAY2 CHECK: FAIL ({r.fails})")
        return 1
    print(f"DAY2 CHECK: PASS ({r.warns} WARN)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
