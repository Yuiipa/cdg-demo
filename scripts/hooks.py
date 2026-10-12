#!/usr/bin/env python
"""Register, remove and test the team hooks in .claude/settings.json.

Usage (from the repo root):
    python scripts/hooks.py enable linkage [--no-selftest]   # self-test, then add to settings.json
    python scripts/hooks.py disable linkage
    python scripts/hooks.py status
    python scripts/hooks.py test linkage | protect | all

Hooks are described by snippet files in .claude/hooks/snippets/<name>.json
({"name", "event", "matcher", "hook": {...}}); Day 2 adds more snippet files.
Tests run each hook command through Git Bash exactly as Claude Code does
(bash -c '<command>', CLAUDE_PROJECT_DIR set, JSON payload on stdin).
Exit codes: 0 = OK, 1 = self-test or a hook test failed, 2 = usage/environment error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SETTINGS = os.path.join(REPO, ".claude", "settings.json")
SNIP_DIR = os.path.join(REPO, ".claude", "hooks", "snippets")
WINDOWS = os.name == "nt"


# ------------------------------------------------------------------ Git Bash
def find_bash() -> str | None:
    cands = []
    env = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if env:
        cands.append(env)
    if WINDOWS:
        cands += [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"]
        lad = os.environ.get("LOCALAPPDATA")
        if lad:
            cands.append(os.path.join(lad, "Programs", "Git", "bin", "bash.exe"))
        try:
            r = subprocess.run(["git", "--exec-path"], capture_output=True, timeout=10)
            exec_path = r.stdout.decode("utf-8", "replace").strip()
            if exec_path:
                root = os.path.abspath(os.path.join(exec_path, "..", "..", ".."))
                cands += [os.path.join(root, "bin", "bash.exe"), os.path.join(root, "usr", "bin", "bash.exe")]
        except Exception:
            pass
    else:
        found = shutil.which("bash")
        if found:
            cands.append(found)
    for c in cands:
        if c and os.path.isfile(c) and "windowsapps" not in c.lower():
            return c
    return None


def git_usr_bin(bash: str) -> str:
    root = os.path.dirname(os.path.dirname(bash))
    if os.path.basename(os.path.dirname(bash)).lower() == "bin" and os.path.basename(root).lower() == "usr":
        return os.path.dirname(bash)
    return os.path.join(root, "usr", "bin")


def run_hook(bash: str, command: str, payload: bytes, env_extra: dict | None = None,
             path_override: str | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = REPO
    if env_extra:
        env.update(env_extra)
    if path_override is not None:
        env["PATH"] = path_override
    try:
        p = subprocess.run([bash, "-c", command], input=payload, capture_output=True, env=env, timeout=60, cwd=REPO)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)
    err = p.stderr.decode("utf-8", "replace").strip()
    return p.returncode, err


def bash_python(bash: str) -> tuple[bool, str]:
    code, out = 0, ""
    try:
        p = subprocess.run([bash, "-c", "python -c 'import sys;print(sys.executable)'"],
                           capture_output=True, timeout=30, cwd=REPO)
        code, out = p.returncode, (p.stdout.decode("utf-8", "replace").strip() or p.stderr.decode("utf-8", "replace").strip())
    except Exception as exc:
        return False, str(exc)
    ok = code == 0 and out and "windowsapps" not in out.lower()
    return bool(ok), out.splitlines()[0] if out else f"exit {code}"


# ------------------------------------------------------------------ snippets / settings
def load_snippets() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not os.path.isdir(SNIP_DIR):
        return out
    for fn in sorted(os.listdir(SNIP_DIR)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(SNIP_DIR, fn), "r", encoding="utf-8-sig") as fh:
                    snip = json.load(fh)
                out[snip.get("name", fn[:-5])] = snip
            except (OSError, ValueError) as exc:
                print(f"WARN  snippet {fn} unreadable: {exc}")
    return out


def read_settings() -> tuple[dict | None, str | None]:
    if not os.path.exists(SETTINGS):
        return {}, None
    try:
        with open(SETTINGS, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None, "top level is not an object"
        return data, None
    except ValueError as exc:
        return None, str(exc)


def write_settings(data: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, SETTINGS)


def enabled_names(settings: dict, snippets: dict[str, dict]) -> list[str]:
    commands = set()
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries or []:
            for h in entry.get("hooks", []) or []:
                commands.add(h.get("command"))
    return [n for n, s in snippets.items() if s.get("hook", {}).get("command") in commands]


# ------------------------------------------------------------------ test cases
def payload(tool: str, tool_input: dict | None) -> bytes:
    obj = {"session_id": "hooks-selftest", "transcript_path": "", "cwd": REPO,
           "permission_mode": "acceptEdits", "hook_event_name": "PreToolUse", "tool_name": tool}
    if tool_input is not None:
        obj["tool_input"] = tool_input
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


DEFAULT_PATTERN = r"(BOOK|CHG|PLAT|SPEC-BK)-\d+"


def ticket_pattern() -> str:
    try:
        with open(os.path.join(REPO, ".claude", "linkage.json"), "r", encoding="utf-8-sig") as fh:
            pat = json.load(fh).get("ticket_pattern") or DEFAULT_PATTERN
        re.compile(pat)
        return pat
    except Exception:
        return DEFAULT_PATTERN


def _refs_ok(pat: str, ticket: str) -> bool:
    return bool(re.search(r"Refs\s*[:=]\s*(?:" + pat + r")", "Refs: " + ticket))


def sample_ticket(pat: str) -> str | None:
    """A ticket id the (team) pattern accepts: BOOK-142 for the kit default."""
    for cand in ("BOOK-142", "PLAT-7", "CHG-1", "SPEC-BK-002"):
        if _refs_ok(pat, cand):
            return cand
    s = re.sub(r"\((?:\?:)?([^|()]*)\|[^()]*\)", r"\1", pat)  # first alternative of each group
    s = s.replace(r"\d+", "1").replace(r"\d", "1").replace("[0-9]+", "1")
    s = re.sub(r"[()^$?+*\\]", "", s)
    return s if s and _refs_ok(pat, s) else None


def foreign_ticket(pat: str) -> str | None:
    for cand in ("ABC-1", "ZZZ-0", "NOPE-404"):
        if not _refs_ok(pat, cand):
            return cand
    return None


def linkage_cases(tmp_msg: str, ok: str = "BOOK-142", bad: str | None = "ABC-1") -> list[tuple[str, bytes, int, bool]]:
    cases = _linkage_cases(tmp_msg)
    if bad is None:
        cases = [c for c in cases if "not a team ticket" not in c[0]]
    bad = bad or "ABC-1"

    def swap(text: str) -> str:  # simultaneous replace (ok may equal "ABC-1")
        return text.replace("BOOK-142", "\0OK\0").replace("ABC-1", bad).replace("\0OK\0", ok)

    out = []
    for label, data, want, nopy in cases:
        if data.startswith(b"{\""):
            data = swap(data.decode("utf-8")).encode("utf-8")
        out.append((swap(label), data, want, nopy))
    return out


def _linkage_cases(tmp_msg: str) -> list[tuple[str, bytes, int, bool]]:
    heredoc = "git commit -m \"$(cat <<'EOF'\nfeat\n\nRefs: BOOK-142\nEOF\n)\""
    B = lambda c: payload("Bash", {"command": c})
    return [
        ('Bash git commit -m "feat: x"', B('git commit -m "feat: x"'), 2, False),
        ('Bash git commit --trailer "Refs: BOOK-142"', B('git commit -m "feat: x" --trailer "Refs: BOOK-142"'), 0, False),
        ('Bash git commit -m ... -m "Refs: BOOK-142"', B('git commit -m "feat: x" -m "Refs: BOOK-142"'), 0, False),
        ('Bash git add -A && git commit -m "x"', B('git add -A && git commit -m "x"'), 2, False),
        ('Bash git -C . commit -am "x"', B('git -C . commit -am "x"'), 2, False),
        ('PowerShell git commit -m "x"', payload("PowerShell", {"command": 'git commit -m "x"'}), 2, False),
        ("Bash git commit -F <file with Refs: BOOK-142>", B(f'git commit -F "{tmp_msg}"'), 0, False),
        ("Bash git status", B("git status"), 0, False),
        ('Bash echo "git commit later"', B('echo "git commit later"'), 0, False),
        ("Bash heredoc message with Refs: BOOK-142", B(heredoc), 0, False),
        ('Bash --trailer "Refs: ABC-1" (not a team ticket)', B('git commit -m "x" --trailer "Refs: ABC-1"'), 2, False),
        ("Monitor payload without command", payload("Monitor", {"description": "watch"}), 0, False),
        ("malformed JSON on stdin", b"{not json", 2, False),
        ("PATH without python (Git usr/bin only)", B("git commit -m x"), 2, True),
    ]


def protect_cases() -> list[tuple[str, bytes, int, bool]]:
    abs_path = os.path.join(REPO, "tests", "test_service.py").replace("/", "\\")
    if WINDOWS:
        abs_path = abs_path.upper()[:-len("test_service.py")] + "Test_Service.py"
    return [
        ("Edit tests/test_rules.py", payload("Edit", {"file_path": "tests/test_rules.py", "old_string": "a", "new_string": "b"}), 2, False),
        ("Write <ABS>\\TESTS\\Test_Service.py (absolute, other case)", payload("Write", {"file_path": abs_path, "content": "x"}), 2, False),
        ("Write tests/test_recurring.py", payload("Write", {"file_path": "tests/test_recurring.py", "content": "x"}), 0, False),
        ("Edit .claude/settings.json", payload("Edit", {"file_path": ".claude/settings.json", "old_string": "a", "new_string": "b"}), 2, False),
        ("Write intent/ทดสอบ.md (Thai file name)", payload("Write", {"file_path": "intent/ทดสอบ.md", "content": "x"}), 0, False),
        ("malformed JSON on stdin", b"[[[", 2, False),
    ]


def selftest_cases(name: str, tmp_msg: str):
    if name == "linkage":
        ok = sample_ticket(ticket_pattern()) or "PLAT-7"
        return [("block: git commit without Refs", payload("Bash", {"command": 'git commit -m "selftest"'}), 2),
                (f"allow: git commit with Refs: {ok}",
                 payload("Bash", {"command": f'git commit -m "selftest" --trailer "Refs: {ok}"'}), 0)]
    if name == "protect":
        return [("block: Edit tests/test_rules.py", payload("Edit", {"file_path": "tests/test_rules.py"}), 2),
                ("allow: Write tests/test_selftest_new.py", payload("Write", {"file_path": "tests/test_selftest_new.py"}), 0)]
    return []


FIX_HINT = ("fix: open a NEW Git Bash terminal, run  source .venv/Scripts/activate  and check "
            "python -c 'import sys;print(sys.executable)'  (must not be WindowsApps); then rerun")


# ------------------------------------------------------------------ commands
def cmd_enable(names: list[str], no_selftest: bool) -> int:
    snippets = load_snippets()
    unknown = [n for n in names if n not in snippets]
    if unknown:
        print(f"FAIL  unknown hook(s): {', '.join(unknown)} (available: {', '.join(snippets) or 'none'})")
        return 2
    settings, err = read_settings()
    if settings is None:
        print(f"FAIL  .claude/settings.json is not valid JSON ({err}); fix it first, nothing was changed")
        return 2
    if not no_selftest:
        bash = find_bash()
        if bash is None:
            print("FAIL  selftest: Git Bash not found (install Git for Windows); settings.json unchanged")
            return 1
        with tempfile.TemporaryDirectory() as td:
            tmp_msg = os.path.join(td, "msg.txt").replace("\\", "/")
            for name in names:
                cmd = snippets[name]["hook"]["command"]
                for label, data, want in selftest_cases(name, tmp_msg):
                    got, err_text = run_hook(bash, cmd, data)
                    if got != want:
                        reason = f"{label} -> exit {got} (want {want})"
                        if err_text:
                            reason += f": {err_text.splitlines()[0][:160]}"
                        print(f"FAIL  selftest {name}: {reason}")
                        print(f"      {FIX_HINT}")
                        print("      settings.json unchanged")
                        return 1
                print(f"SELFTEST {name}: PASS")
    else:
        print("INFO  selftest skipped (--no-selftest)")

    hooks = settings.setdefault("hooks", {})
    for name in names:
        snip = snippets[name]
        event, matcher, hook = snip["event"], snip["matcher"], dict(snip["hook"])
        entries = hooks.setdefault(event, [])
        entry = next((e for e in entries if e.get("matcher") == matcher), None)
        if entry is None:
            entry = {"matcher": matcher, "hooks": []}
            entries.append(entry)
        if any(h.get("command") == hook.get("command") for h in entry.setdefault("hooks", [])):
            print(f"INFO  {name} already enabled")
        else:
            entry["hooks"].append(hook)
        print(f"ENABLED {name} ({event} {matcher})")
    write_settings(settings)
    print("next: git diff .claude/settings.json")
    return 0


def cmd_disable(names: list[str]) -> int:
    snippets = load_snippets()
    unknown = [n for n in names if n not in snippets]
    if unknown:
        print(f"FAIL  unknown hook(s): {', '.join(unknown)} (available: {', '.join(snippets) or 'none'})")
        return 2
    settings, err = read_settings()
    if settings is None:
        print(f"FAIL  .claude/settings.json is not valid JSON ({err}); nothing was changed")
        return 2
    commands = {snippets[n]["hook"]["command"] for n in names}
    hooks = settings.get("hooks") or {}
    removed = 0
    for event in list(hooks):
        new_entries = []
        for entry in hooks[event] or []:
            kept = [h for h in entry.get("hooks", []) if h.get("command") not in commands]
            removed += len(entry.get("hooks", [])) - len(kept)
            if kept:
                entry["hooks"] = kept
                new_entries.append(entry)
        if new_entries:
            hooks[event] = new_entries
        else:
            del hooks[event]
    if "hooks" in settings and not hooks:
        del settings["hooks"]
    if removed:
        write_settings(settings)
    for n in names:
        print(f"DISABLED {n}" if removed else f"INFO  {n} was not enabled")
    if removed:
        print("next: git diff .claude/settings.json")
    return 0


def cmd_status() -> int:
    snippets = load_snippets()
    settings, err = read_settings()
    bad = 0
    if settings is None:
        print(f"FAIL  settings.json valid JSON ({err})")
        bad += 1
        settings = {}
    elif not os.path.exists(SETTINGS):
        print("WARN  .claude/settings.json missing")
    else:
        print("PASS  settings.json valid JSON")
    names = enabled_names(settings, snippets)
    print(f"INFO  enabled: {', '.join(names) if names else '(none)'}")
    print(f"INFO  available: {', '.join(snippets) if snippets else '(none)'}")
    bash = find_bash()
    if bash is None:
        print("WARN  git-bash python: Git Bash not found")
    else:
        ok, where = bash_python(bash)
        print(f"{'PASS' if ok else 'WARN'}  git-bash python: {where.replace(chr(92), '/')}")
    print(f"HOOKS: {'PASS' if not bad else 'FAIL'}")
    return 0 if not bad else 1


def cmd_test(which: str) -> int:
    snippets = load_snippets()
    names = list(snippets) if which == "all" else [which]
    names = [n for n in names if n in ("linkage", "protect")]
    if not names or (which != "all" and which not in snippets):
        print(f"FAIL  unknown hook '{which}' (use linkage, protect or all)")
        return 2
    bash = find_bash()
    if bash is None:
        print("FAIL  Git Bash not found (install Git for Windows)")
        return 2
    pat = ticket_pattern()
    ok_ticket = sample_ticket(pat)
    bad_ticket = foreign_ticket(pat)
    if "linkage" in names and ok_ticket is None:
        print(f"FAIL  cannot build a sample ticket for pattern {pat} (check .claude/linkage.json)")
        return 2
    if pat != DEFAULT_PATTERN:
        print(f"INFO  team ticket pattern {pat} · sample ticket {ok_ticket}")
    total = passed = 0
    with tempfile.TemporaryDirectory() as td:
        tmp_msg = os.path.join(td, "msg.txt").replace("\\", "/")
        with open(tmp_msg, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"feat: from file\n\nRefs: {ok_ticket}\n")
        for name in names:
            cmd = snippets[name]["hook"]["command"]
            cases = linkage_cases(tmp_msg, ok_ticket, bad_ticket) if name == "linkage" else protect_cases()
            for label, data, want, no_python in cases:
                total += 1
                got, err_text = run_hook(bash, cmd, data, path_override=git_usr_bin(bash) if no_python else None)
                if got == want:
                    passed += 1
                    print(f"PASS  {name}: {label} -> exit {got}")
                else:
                    first = err_text.splitlines()[0][:160] if err_text else ""
                    print(f"FAIL  {name}: {label} -> exit {got} (want {want}) {first}".rstrip())
    print(f"HOOK TESTS: {passed}/{total} {'PASS' if passed == total else 'FAIL'}")
    return 0 if passed == total else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hooks.py", description="Enable, disable, show and test team hooks (.claude/settings.json).")
    sub = ap.add_subparsers(dest="cmd")
    p_en = sub.add_parser("enable", help="self-test, then register hook(s)")
    p_en.add_argument("names", nargs="+")
    p_en.add_argument("--no-selftest", action="store_true", help="skip the Git Bash self-test (kit build only)")
    p_dis = sub.add_parser("disable", help="remove hook(s) from settings.json")
    p_dis.add_argument("names", nargs="+")
    sub.add_parser("status", help="show enabled hooks and the python Git Bash will use")
    p_t = sub.add_parser("test", help="run the hook test table through Git Bash")
    p_t.add_argument("which", choices=["linkage", "protect", "all"])
    args = ap.parse_args(argv)
    if args.cmd == "enable":
        return cmd_enable(args.names, args.no_selftest)
    if args.cmd == "disable":
        return cmd_disable(args.names)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "test":
        return cmd_test(args.which)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
