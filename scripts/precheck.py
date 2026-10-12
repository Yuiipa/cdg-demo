#!/usr/bin/env python
"""Readiness check for Day 1 (run with the TA at 08:30, from the repo root).

Usage:
    source .venv/Scripts/activate
    python scripts/precheck.py [--skip-claude] [--no-mcp]

PowerShell: .\\.venv\\Scripts\\python.exe scripts\\precheck.py
Rows: PASS / WARN / FAIL / INFO. Last line: "PRECHECK: PASS (n WARN)" (exit 0)
or "PRECHECK: FAIL (n)" (exit 1). WARN rows never block class.
--skip-claude skips the claude and MCP rows; --no-mcp skips only the MCP row.
"""
from __future__ import annotations

import argparse
import glob
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
CLAUDE_VERSION = "2.1.296"


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


def same_path(a: str, b: str) -> bool:
    na = os.path.normcase(os.path.realpath(os.path.abspath(a)))
    nb = os.path.normcase(os.path.realpath(os.path.abspath(b)))
    return na == nb


def venv_python() -> str | None:
    for cand in (os.path.join(REPO, ".venv", "Scripts", "python.exe"), os.path.join(REPO, ".venv", "bin", "python")):
        if os.path.isfile(cand):
            return cand
    return None


def shim(path: str) -> list[str]:
    return ["cmd", "/c", path] if path.lower().endswith((".cmd", ".bat")) else [path]


def acceptance_dir() -> str:
    env = os.environ.get("CDG_ACCEPTANCE_DIR")
    return os.path.abspath(env) if env else os.path.abspath(os.path.join(REPO, "..", "cdg-acceptance"))


def find_bash() -> str | None:
    cands = []
    if os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
        cands.append(os.environ["CLAUDE_CODE_GIT_BASH_PATH"])
    if WINDOWS:
        cands += [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"]
        if os.environ.get("LOCALAPPDATA"):
            cands.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Git", "bin", "bash.exe"))
        code, out = run(["git", "--exec-path"], timeout=10)
        if code == 0 and out.strip():
            root = os.path.abspath(os.path.join(out.strip(), "..", "..", ".."))
            cands += [os.path.join(root, "bin", "bash.exe"), os.path.join(root, "usr", "bin", "bash.exe")]
    else:
        if shutil.which("bash"):
            cands.append(shutil.which("bash"))
    for c in cands:
        if c and os.path.isfile(c) and "windowsapps" not in c.lower():
            return c
    return None


# ------------------------------------------------------------------ rows
def row_python(r: Rows) -> None:
    v = sys.version_info
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    repo_venv = os.path.join(REPO, ".venv")
    label = "python >= 3.11 in .venv"
    if not os.path.isdir(repo_venv):
        r.row("FAIL", label, "no .venv yet: python -m venv .venv  then  source .venv/Scripts/activate")
    elif not in_venv or not same_path(sys.prefix, repo_venv):
        r.row("FAIL", label, "not in the repo venv: source .venv/Scripts/activate  (PowerShell: .\\.venv\\Scripts\\python.exe scripts\\precheck.py)")
    elif v < (3, 10):
        r.row("FAIL", label + f" (found {v.major}.{v.minor})", "install Python 3.11+ and recreate .venv")
    elif v < (3, 11):
        r.row("WARN", label + f" (found {v.major}.{v.minor})", "3.11+ recommended")
    else:
        r.row("PASS", label)


def row_terminal(r: Rows) -> None:
    if os.environ.get("MSYSTEM"):
        r.row("PASS", "terminal: Git Bash")
    else:
        r.row("WARN", "terminal: Git Bash", "VS Code: Terminal → New Terminal → ˅ → Git Bash")


def pytest_counts(out: str) -> tuple[int, int]:
    for line in reversed(out.splitlines()):
        if re.search(r"\b(passed|failed|errors?|no tests ran)\b", line) and re.search(r"\bin [\d.]+s", line):
            m = re.search(r"(\d+) passed", line)
            failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|errors?)\b", line))
            return (int(m.group(1)) if m else 0), failed
    return 0, -1


def row_pytest(r: Rows) -> None:
    py = venv_python() or sys.executable
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    code, out = run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], timeout=300, env=env)
    passed, failed = pytest_counts(out)
    fix = "python -m pip install -r requirements-dev.txt   (offline: --no-index --find-links ../wheels)"
    if "No module named pytest" in out:
        r.row("FAIL", "pytest: not installed", fix)
    elif failed == 0 and passed > 0:
        r.row("PASS", f"pytest: {passed} passed")
    elif failed < 0:
        tail = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
        r.row("FAIL", f"pytest: no result ({tail[:100]})", fix)
    else:
        r.row("FAIL", f"pytest: {passed} passed, {failed} failed", "run python -m pytest and show the TA")


def row_git(r: Rows) -> None:
    code, out = run(["git", "--version"], timeout=20)
    m = re.search(r"(\d+)\.(\d+)", out)
    label = "git >= 2.40 · tag checkpoint/mw-start"
    if code != 0 or not m:
        r.row("FAIL", label, "install Git for Windows (includes Git Bash)")
        return
    ver = (int(m.group(1)), int(m.group(2)))
    tag_code, _ = run(["git", "rev-parse", "-q", "--verify", "refs/tags/checkpoint/mw-start"], timeout=20)
    if tag_code != 0:
        r.row("FAIL", label + " (tag missing)", "re-extract the kit zip (keep the .git folder)")
    elif ver < (2, 32):
        r.row("FAIL", label + f" (git {ver[0]}.{ver[1]}: no --trailer)", "update Git for Windows")
    elif ver < (2, 40):
        r.row("WARN", label + f" (git {ver[0]}.{ver[1]})", "update Git for Windows when you can")
    else:
        r.row("PASS", label)


def row_identity(r: Rows) -> None:
    _, name = run(["git", "config", "user.name"], timeout=20)
    _, email = run(["git", "config", "user.email"], timeout=20)
    if name.strip() and email.strip():
        r.row("PASS", "git identity")
    else:
        r.row("FAIL", "git identity",
              'git config --global user.name "ชื่อคุณ"\ngit config --global user.email "you@example.com"')


def row_kit_path(r: Rows) -> None:
    p = REPO
    bad = []
    if not p.isascii():
        bad.append("non-ASCII")
    if " " in p:
        bad.append("space")
    if "onedrive" in p.lower():
        bad.append("OneDrive")
    if bad:
        r.row("WARN", f"kit path ({', '.join(bad)})", "extract to C:\\work  (C:\\work\\cdg-kit-v3\\cdg-claude-code-demo)")
    else:
        r.row("PASS", "kit path")


def row_bash_python(r: Rows) -> None:
    label = "Git Bash python is not a Store stub"
    bash = find_bash()
    if bash is None:
        r.row("WARN", label + " (Git Bash not found)", "install Git for Windows; fix before 13:45 (hooks)")
        return
    code, out = run([bash, "-c", "python -c 'import sys;print(sys.executable)'"], timeout=30)
    where = out.strip().splitlines()[-1] if out.strip() else ""
    if code == 0 and where and "windowsapps" not in where.lower():
        r.row("PASS", label)
    else:
        r.row("WARN", label + (f" ({where[:80]})" if where else f" (exit {code})"),
              "fix before 13:45 (hooks): open a new Git Bash, source .venv/Scripts/activate, "
              "or turn off Settings → Apps → Advanced app settings → App execution aliases → python.exe")


def autoupdate_disabled() -> bool:
    if os.environ.get("DISABLE_AUTOUPDATER") == "1":
        return True
    try:
        with open(os.path.join(os.path.expanduser("~"), ".claude", "settings.json"), "r", encoding="utf-8-sig") as fh:
            if str((json.load(fh).get("env") or {}).get("DISABLE_AUTOUPDATER")) == "1":
                return True
    except (OSError, ValueError, AttributeError):
        pass
    if WINDOWS:  # set with setx after this terminal was opened
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                val, _ = winreg.QueryValueEx(key, "DISABLE_AUTOUPDATER")
                return str(val) == "1"
        except OSError:
            pass
    return False


def row_claude(r: Rows) -> list[str] | None:
    label = f"claude {CLAUDE_VERSION} · Auto-updates: disabled"
    path = shutil.which("claude")
    if not path:
        r.row("WARN", label + " (claude not found)", "install Claude Code, then open a new terminal")
        return None
    base = shim(path)
    code, out = run(base + ["--version"], timeout=20)
    m = re.search(r"\d+\.\d+\.\d+", out)
    ver = m.group(0) if m else out.strip()[:40]
    au = autoupdate_disabled()
    if CLAUDE_VERSION in out and au:
        r.row("PASS", label)
    else:
        why = []
        if CLAUDE_VERSION not in out:
            why.append(f"found {ver or 'unknown'}")
        if not au:
            why.append("auto-update not disabled")
        r.row("WARN", label + f" ({'; '.join(why)})", "setx DISABLE_AUTOUPDATER 1  (then open a new terminal); a version mismatch does not block class")
    return base


def row_mcp(r: Rows, base: list[str] | None) -> None:
    label = "MCP internal-tools connected"
    py = venv_python() or sys.executable
    code, _ = run([py, "-c", "import mcp"], timeout=60)
    if code != 0:
        r.row("WARN", label + " (mcp not installed)", "python -m pip install -r requirements-mcp.txt   · D1-L2 can use the ticket file fallback")
        return
    if base is None:
        r.row("WARN", label + " (claude not found)", "D1-L2 will use the ticket file fallback")
        return

    def connected() -> tuple[bool, str]:
        c, o = run(base + ["mcp", "get", "internal-tools"], timeout=60)
        return ("Connected" in o and "Failed" not in o), o

    ok, out = connected()
    if not ok and ("No MCP server" in out or "not found" in out.lower() or "internal-tools" not in out):
        run([sys.executable, os.path.join(HERE, "setup_mcp.py")], timeout=180)
        ok, out = connected()
    if ok:
        r.row("PASS", label)
    else:
        r.row("WARN", label, "D1-L2 will use the ticket file fallback (python scripts/roles.py reveal ticket); TA: python scripts/setup_mcp.py")


def row_acceptance(r: Rows) -> None:
    acc = acceptance_dir()
    missing = [p for p in ("check.py", os.path.join("savepoints", "day1.bundle")) if not os.path.isfile(os.path.join(acc, p))]
    if missing:
        r.row("FAIL", "../cdg-acceptance found", "keep the kit folders together (cdg-kit-v3/cdg-acceptance next to the repo)")
    else:
        r.row("PASS", "../cdg-acceptance found")


def row_fallback(r: Rows) -> None:
    label = "fallback skills + node"
    fb = os.path.isfile(os.path.join(REPO, "..", "fallback-skills", "tdd", "SKILL.md"))
    node = shutil.which("node")
    npx = shutil.which("npx")
    node_ok = bool(node) and run(shim(node) + ["--version"], timeout=20)[0] == 0
    npx_ok = bool(npx) and run(shim(npx) + ["--version"], timeout=60)[0] == 0
    if fb and node_ok and npx_ok:
        r.row("PASS", label)
    elif fb:
        r.row("INFO", label + " (node/npx missing)", "13:00: use the cp fallback from ../fallback-skills (LABS.md §5)")
    else:
        r.row("WARN", label + " (../fallback-skills missing)", "needed at 13:00: keep the kit folders together")


def row_leaks(r: Rows) -> None:
    code, out = run([sys.executable, os.path.join(HERE, "doctor.py"), "--leaks", "--pristine"], timeout=120)
    if code == 0:
        r.row("PASS", "leak scan")
    else:
        details = "\n".join(l for l in out.splitlines() if l.startswith("FAIL"))[:800]
        r.row("FAIL", "leak scan", (details + "\n" if details else "") + "TA: re-extract the kit zip")


def row_managed(r: Rows) -> None:
    keys = ("allowManagedHooksOnly", "disableAllHooks", "allowManagedPermissionRulesOnly", "disableSideloadFlags")
    files = [r"C:\Program Files\ClaudeCode\managed-settings.json"] + sorted(glob.glob(r"C:\Program Files\ClaudeCode\managed-settings.d\*.json"))
    if not WINDOWS:
        files = ["/Library/Application Support/ClaudeCode/managed-settings.json", "/etc/claude-code/managed-settings.json"]
    hits = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        hits += [k for k in keys if data.get(k)]
    if hits:
        r.row("WARN", "managed policy disables hooks -> tell instructor", ", ".join(sorted(set(hits))))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="precheck.py", description="Day-1 readiness check (TA, 08:30).")
    ap.add_argument("--skip-claude", action="store_true", help="skip the claude and MCP rows")
    ap.add_argument("--no-mcp", action="store_true", help="skip the MCP row")
    args = ap.parse_args(argv)

    r = Rows()
    row_python(r)
    row_terminal(r)
    row_pytest(r)
    row_git(r)
    row_identity(r)
    row_kit_path(r)
    row_bash_python(r)
    if not args.skip_claude:
        base = row_claude(r)
        if not args.no_mcp:
            row_mcp(r, base)
    row_acceptance(r)
    row_fallback(r)
    row_leaks(r)
    row_managed(r)
    if r.fails:
        print(f"PRECHECK: FAIL ({r.fails})")
        return 1
    print(f"PRECHECK: PASS ({r.warns} WARN)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
