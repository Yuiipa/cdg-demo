#!/usr/bin/env python
"""Stop hook: Claude may end its turn only when pytest is green (max 3 rounds).

Registered by .claude/hooks/snippets/stop.json as  python "<hook>"  (no "|| exit 2":
if python is missing the hook fails OPEN and the turn ends). Input is the Stop payload
on stdin ({"hook_event_name": "Stop", "stop_hook_active": ..., "cwd": ..., "session_id": ...}).

Order of checks (first hit wins):
  1. env CDG_LOOP_OWNER in {off, wrapper, eval, ci}      -> allow   (another loop owns the stop rule)
  2. artifacts/escalation.md exists                        -> allow   (escape hatch: a human must decide)
  3. protected tests differ from `git merge-base main HEAD` -> block  (test เดิมถูกแก้; round not counted)
  4. python -m pytest -q -p no:cacheprovider  exit 0       -> allow   (artifacts/.round deleted)
  5. failing: round n = artifacts/.round + 1; n <= 2 block (fix), n == 3 block (escalate), n > 3 allow

Block = JSON {"decision": "block", "reason": "..."} on stdout, exit 0.  Allow = no output, exit 0.
Every decision is appended to artifacts/hook_decisions.jsonl ("hook": "stop"). pytest output goes to
artifacts/last_pytest.txt and artifacts/round_<n>.txt. Unparseable input -> allow (fail-open).

Env overrides (used by scripts/hooks.py test stop; never set them in a real session):
  CDG_STOP_FAKE_PYTEST=pass|fail   pretend instead of running pytest
  CDG_STOP_STATE_DIR=<dir>         where .round / last_pytest.txt / escalation.md / the log live
Standalone: stdlib only, no imports from other kit files.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOOK = "stop"
MAX_ROUNDS = 3
PYTEST_TIMEOUT = 150
GIT_TIMEOUT = 20
TAIL_LINES = 25
OWNER_OFF = {"off", "wrapper", "eval", "ci"}
DEFAULT_PROTECTED_TESTS = ["tests/test_rules.py", "tests/test_service.py"]
WINDOWS = os.name == "nt"

REASON_TAMPER = (
    "Stop hook: test เดิมถูกแก้ ({files}) กู้คืนด้วย git checkout {base7} -- {files_args} แล้วแก้โค้ดแทน "
    "หรือถ้า spec ขัดกับ test เดิม ให้เขียน artifacts/escalation.md ตาม intent/TEMPLATES/escalation.template.md แล้วจบเทิร์น"
)
REASON_FAIL = (
    "Stop hook: pytest ยังไม่ผ่าน (รอบ {n}/3): {summary}. แก้โค้ดใน booking/ ให้ test ผ่าน ห้ามแก้ test เดิม ({protected}) "
    "แล้วรัน python -m pytest ใหม่ก่อนจบเทิร์น ถ้า spec ขัดกับ test เดิม ให้เขียน artifacts/escalation.md แล้วจบ"
)
REASON_ESCALATE = (
    "Stop hook: รอบ 3/3 ยังไม่ผ่าน หยุดแก้โค้ด เขียน artifacts/escalation.md (Tried / Hypotheses / Need from human) "
    "ตาม intent/TEMPLATES/escalation.template.md แล้วจบเทิร์น"
)


# ------------------------------------------------------------------ paths / state
def win_path(path: str) -> str:
    """Git Bash style /c/work/x -> C:/work/x on Windows; other paths unchanged."""
    if WINDOWS and path:
        m = re.match(r"^/([a-zA-Z])/(.*)$", path.replace("\\", "/"))
        if m:
            return f"{m.group(1).upper()}:/{m.group(2)}"
    return path


def state_dir(project: str) -> str:
    override = os.environ.get("CDG_STOP_STATE_DIR") or ""
    return win_path(override) if override.strip() else os.path.join(project, "artifacts")


def ensure_dir(folder: str) -> None:
    os.makedirs(folder, exist_ok=True)
    ignore = os.path.join(folder, ".gitignore")
    if not os.path.exists(ignore):  # self-ignoring folder: never swept into a team repo commit
        with open(ignore, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("*\n")


def log(state: str, decision: str, reason: str, rnd: int) -> None:
    try:
        ensure_dir(state)
        rec = {"hook": HOOK, "decision": decision, "reason": reason, "round": rnd,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        with open(os.path.join(state, "hook_decisions.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging never changes the decision


def read_round(state: str) -> int:
    try:
        with open(os.path.join(state, ".round"), "r", encoding="utf-8-sig") as fh:
            return max(0, int(fh.read().strip() or "0"))
    except Exception:
        return 0


def write_round(state: str, rnd: int) -> None:
    try:
        ensure_dir(state)
        with open(os.path.join(state, ".round"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"{rnd}\n")
    except Exception:
        pass


def clear_round(state: str) -> None:
    try:
        os.remove(os.path.join(state, ".round"))
    except FileNotFoundError:
        pass
    except Exception:
        pass


def save_text(state: str, name: str, text: str) -> None:
    try:
        ensure_dir(state)
        with open(os.path.join(state, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except Exception:
        pass


# ------------------------------------------------------------------ protected tests / git
def protected_tests(project: str) -> list[str]:
    """Protected test FILES (entries under tests/) from .claude/protected_paths.json; kit default otherwise."""
    items: list[str] = []
    try:
        with open(os.path.join(project, ".claude", "protected_paths.json"), "r", encoding="utf-8-sig") as fh:
            for entry in json.load(fh).get("protected", []):
                e = str(entry).replace("\\", "/")
                if e.startswith("./"):
                    e = e[2:]
                if e.startswith("tests/") and not e.endswith("/"):
                    items.append(e)
    except Exception:
        items = []
    return items or list(DEFAULT_PROTECTED_TESTS)


def git(args: list[str], project: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], cwd=project, capture_output=True, timeout=GIT_TIMEOUT,
                           stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return 127, ""
    return p.returncode, p.stdout.decode("utf-8", "replace")


def merge_base(project: str) -> str:
    code, out = git(["merge-base", "main", "HEAD"], project)
    if code == 0 and out.strip():
        return out.strip()
    code, out = git(["rev-parse", "HEAD"], project)
    return out.strip() if code == 0 and out.strip() else "HEAD"


def protected_diff(project: str, base: str, files: list[str]) -> list[str]:
    """Protected test files whose working-tree content differs from <base>; [] when unchanged or git fails."""
    code, _ = git(["diff", "--quiet", base, "--", *files], project)
    if code != 1:  # 0 = unchanged, >1 = git error (fail-open)
        return []
    code, out = git(["diff", "--name-only", base, "--", *files], project)
    changed = [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()] if code == 0 else []
    return changed or list(files)


# ------------------------------------------------------------------ pytest
def python_for_pytest(project: str) -> str:
    try:
        import importlib.util
        if importlib.util.find_spec("pytest") is not None:
            return sys.executable
    except Exception:
        pass
    for cand in (os.path.join(project, ".venv", "Scripts", "python.exe"), os.path.join(project, ".venv", "bin", "python")):
        if os.path.isfile(cand):
            return cand
    return sys.executable


def run_pytest(project: str) -> tuple[int | None, str]:
    """(exit code, combined output). exit None = timeout."""
    fake = (os.environ.get("CDG_STOP_FAKE_PYTEST") or "").strip().lower()
    if fake == "pass":
        return 0, "27 passed in 0.01s  [CDG_STOP_FAKE_PYTEST=pass]\n"
    if fake == "fail":
        return 1, ("FAILED tests/test_fake.py::test_fake - AssertionError  [CDG_STOP_FAKE_PYTEST=fail]\n"
                   "1 failed, 26 passed in 0.01s\n")
    cmd = [python_for_pytest(project), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    try:
        p = subprocess.run(cmd, cwd=project, capture_output=True, timeout=PYTEST_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else ""
        return None, partial + f"\n[stop_guard] pytest timeout after {PYTEST_TIMEOUT}s\n"
    except OSError as exc:
        return -1, f"[stop_guard] cannot run pytest: {exc}\n"
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def summarize(output: str) -> tuple[int, int, int, str]:
    """(passed, failed, errors, summary text) from the last pytest summary line."""
    passed = failed = errors = 0
    line = ""
    for ln in reversed(output.splitlines()):
        if re.search(r"\d+ (passed|failed|error)", ln) or "no tests ran" in ln:
            line = ln.strip(" =")
            break
    for key, pat in (("passed", r"(\d+) passed"), ("failed", r"(\d+) failed"), ("errors", r"(\d+) errors?\b")):
        m = re.search(pat, line)
        n = int(m.group(1)) if m else 0
        if key == "passed":
            passed = n
        elif key == "failed":
            failed = n
        else:
            errors = n
    summary = f"{failed} failed, {passed} passed"
    if errors:
        summary += f", {errors} error"
    if not line.strip() and not (passed or failed or errors):
        summary = "pytest ไม่มีบรรทัดสรุป"
    return passed, failed, errors, summary


def tail(output: str, n: int = TAIL_LINES) -> str:
    lines = [ln.rstrip() for ln in output.splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


# ------------------------------------------------------------------ decisions
def allow(state: str, reason: str, rnd: int) -> int:
    log(state, "allow", reason, rnd)
    return 0


def block(state: str, reason_tag: str, text: str, rnd: int) -> int:
    log(state, "block", reason_tag, rnd)
    sys.stdout.write(json.dumps({"decision": "block", "reason": text}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


def main() -> int:
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    env_project = win_path(os.environ.get("CLAUDE_PROJECT_DIR") or "")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception:
        state = state_dir(env_project or os.getcwd())
        return allow(state, "unparseable input (allow)", read_round(state))
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd").strip() else os.getcwd()
    project = env_project or win_path(cwd)
    state = state_dir(project)
    rounds = read_round(state)

    # 1. another loop owns the stop rule (wrapper / eval / CI)
    owner = (os.environ.get("CDG_LOOP_OWNER") or "").strip().lower()
    if owner in OWNER_OFF:
        return allow(state, "owner off", rounds)
    # 2. escape hatch: a human must decide
    if os.path.exists(os.path.join(state, "escalation.md")):
        return allow(state, "escalated", rounds)
    # 3. the agent that fixes code must not change the check on that code
    protected = protected_tests(project)
    base = merge_base(project)
    changed = protected_diff(project, base, protected)
    if changed:
        text = REASON_TAMPER.format(files=", ".join(changed), base7=base[:7], files_args=" ".join(changed))
        return block(state, "tamper", text, rounds)
    # 4. the oracle (only inside a project: never let pytest crawl an unrelated folder)
    if not any(os.path.exists(os.path.join(project, m)) for m in ("tests", "pyproject.toml", "pytest.ini", "setup.cfg")):
        return allow(state, "no project markers (allow)", rounds)
    code, output = run_pytest(project)
    save_text(state, "last_pytest.txt", output)
    if code is None:
        return allow(state, "pytest timeout (allow)", rounds)
    if code == 0:
        clear_round(state)
        return allow(state, "pass", rounds)
    if code == 5 and "no tests ran" in output:
        clear_round(state)
        return allow(state, "no tests (allow)", rounds)
    if "No module named pytest" in output or code == -1:
        return allow(state, "pytest not available (allow)", rounds)
    # 5. failing: bounded retry
    rnd = rounds + 1
    write_round(state, rnd)
    save_text(state, f"round_{rnd}.txt", output)
    if rnd < MAX_ROUNDS:
        _, _, _, summary = summarize(output)
        text = REASON_FAIL.format(n=rnd, summary=summary, protected=", ".join(protected))
        return block(state, f"fail r{rnd}", text + "\n\n" + tail(output), rnd)
    if rnd == MAX_ROUNDS:
        return block(state, f"fail r{rnd} escalate", REASON_ESCALATE, rnd)
    return allow(state, "max rounds", rnd)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # any crash lets the turn end (fail-open) but leaves a trace
        try:
            sys.stderr.write(f"stop_guard: internal error ({type(exc).__name__}: {exc}) -> allow\n")
        except Exception:
            pass
        sys.exit(0)
