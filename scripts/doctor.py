#!/usr/bin/env python
"""doctor: check a lab document, the Day-1 state of the repo, or the kit for leaks.

Usage (from the repo root):
    python scripts/doctor.py --check claude-md CLAUDE.md
    python scripts/doctor.py --check intent  intent/recurring-booking/intent.md
    python scripts/doctor.py --check spec    intent/recurring-booking/spec.md
    python scripts/doctor.py --check plan    intent/recurring-booking/plan.md
    python scripts/doctor.py --stage d1
    python scripts/doctor.py --leaks [--pristine]

Each run prints PASS/WARN/FAIL/INFO rows and ends with "DOCTOR <kind>: PASS|FAIL".
Exit 0 = no FAIL row, 1 = at least one FAIL row, 2 = usage/environment error
(missing file, ../cdg-acceptance not found, git error).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE_MD_HEADINGS = ["Commands", "Conventions", "Architecture", "Things Claude gets wrong", "Verifying your work"]
INTENT_SECTIONS = ["Problem", "Proposed outcome", "Affected users and systems", "Constraints", "Open questions"]
PLAN_SECTIONS = ["Files that change", "Order of work", "Risks", "Proof"]
POLICIES = ["booking-policy", "ux-messages", "security-baseline"]
CONTRACT_RE = re.compile(r"create_recurring_booking\s*\(([^)]*)\)\s*->\s*[`*]*\s*[\w.]*RecurringResult")
CONTRACT_PARAMS = ["room_id", "user_id", "start", "end", "weeks"]


class Report:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.fails = 0
        self.warns = 0

    def row(self, status: str, text: str) -> None:
        if status == "FAIL":
            self.fails += 1
        elif status == "WARN":
            self.warns += 1
        print(f"{status:<4}  {text}")

    def check(self, ok: bool, text: str, fail_hint: str = "") -> bool:
        self.row("PASS" if ok else "FAIL", text if ok or not fail_hint else f"{text}  ({fail_hint})")
        return ok

    def finish(self) -> int:
        verdict = "PASS" if self.fails == 0 else "FAIL"
        print(f"DOCTOR {self.kind}: {verdict}")
        return 0 if self.fails == 0 else 1


# ------------------------------------------------------------------ helpers
def repo_root() -> str:
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "booking")) or os.path.isdir(os.path.join(cwd, ".git")):
        return cwd
    return os.path.dirname(HERE)


def acceptance_dir(repo: str) -> str:
    env = os.environ.get("CDG_ACCEPTANCE_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(repo, "..", "cdg-acceptance"))


def venv_python(repo: str) -> str:
    for cand in (os.path.join(repo, ".venv", "Scripts", "python.exe"), os.path.join(repo, ".venv", "bin", "python")):
        if os.path.isfile(cand):
            return cand
    return sys.executable


def child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(cmd: list[str], cwd: str, timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=child_env())
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=cwd, capture_output=True)


def read_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read().splitlines()


def sections(lines: list[str]) -> dict[str, list[str]]:
    """'## Heading' (level 2 or 3) -> body lines, keyed by lower-case heading text."""
    out: dict[str, list[str]] = {}
    current = None
    for line in lines:
        m = re.match(r"^\s{0,3}#{2,3}\s+(.+?)\s*#*\s*$", line)
        if m:
            current = m.group(1).strip().strip("*").strip().lower()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return out


def find_section(secs: dict[str, list[str]], name: str) -> list[str] | None:
    name = name.lower()
    for key, body in secs.items():
        if key == name or key.startswith(name):
            return body
    return None


def content_lines(body: list[str] | None) -> list[str]:
    return [l for l in (body or []) if l.strip() and not l.strip().startswith("<!--")]


# ------------------------------------------------------------------ --check
def check_claude_md(path: str, rep: Report) -> None:
    lines = read_lines(path)
    secs = sections(lines)
    missing = [h for h in CLAUDE_MD_HEADINGS if find_section(secs, h) is None]
    rep.check(not missing, f"headings {5 - len(missing)}/5", "missing: " + ", ".join(f"## {m}" for m in missing))
    rep.check(len(lines) <= 60, f"lines {len(lines)} <= 60", "cut it to one page")


def run_pii(path: str) -> tuple[int, str]:
    scanner = os.path.join(HERE, "pii_scan.py")
    if not os.path.isfile(scanner):
        return 2, "scripts/pii_scan.py missing"
    code, out = run([sys.executable, scanner, path], cwd=os.getcwd(), timeout=60)
    last = [l for l in out.splitlines() if l.strip()]
    return code, (last[-1] if last else out.strip())


def check_intent(path: str, rep: Report) -> None:
    lines = read_lines(path)
    text = "\n".join(lines)
    secs = sections(lines)
    missing = [s for s in INTENT_SECTIONS if find_section(secs, s) is None]
    rep.check(not missing, f"sections {5 - len(missing)}/5", "missing: " + ", ".join(f"## {m}" for m in missing))
    m = re.search(r"Source:\s*[`*]*\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)", text)
    rep.check(bool(m), f"Source: {m.group(1)} line present" if m else "Source: BOOK-… line present",
              "add a line 'Source: BOOK-142'")
    rep.check(len(lines) <= 60, f"lines {len(lines)} <= 60", "keep the intent to one page")
    code, summary = run_pii(path)
    rep.check(code == 0, "PII: none" if code == 0 else (summary if summary.startswith("PII") else f"PII: {summary}"),
              "replace names/phones/e-mails with roles, then rerun: python scripts/pii_scan.py " + path.replace(chr(92), "/"))
    status = re.search(r"Status:\s*[`*]*\s*([A-Za-z]+)", text)
    st = status.group(1).lower() if status else ""
    if st == "accepted":
        rep.row("PASS", "Status: accepted")
    elif st == "proposed":
        rep.row("WARN", "Status: proposed (needs PO accept)")
    else:
        rep.row("WARN", f"Status: {st or 'missing'} (expected proposed -> accepted)")
    code_hits = []
    for pat in (r"\b[A-Za-z_][A-Za-z0-9_]*\(", r"\bdef ", r"\bclass ", r"\b\w+\.py\b", r"\b[a-z]+_[a-z0-9_]+\("):
        for ln in lines:
            if ln.lstrip().startswith(("Source:", "Author:")):
                continue
            mm = re.search(pat, ln)
            if mm:
                code_hits.append(mm.group(0).strip())
                break
    if code_hits:
        rep.row("WARN", "code identifiers: " + ", ".join(sorted(set(code_hits))[:4]) + " (intent = problem, not solution design)")
    else:
        rep.row("PASS", "code identifiers: none")


def check_spec(path: str, rep: Report) -> None:
    lines = read_lines(path)
    text = "\n".join(lines)
    secs = sections(lines)
    req = find_section(secs, "Requirements")
    ids = sorted({int(x) for x in re.findall(r"\bR([1-9]\d?)\b", "\n".join(req or []))})
    rep.check(len(ids) >= 5, f"requirements R1..R{max(ids) if ids else 0} >= 5" if ids else "requirements R1..Rn >= 5",
              f"found {len(ids)} R-items under ## Requirements")
    design = find_section(secs, "Design")
    ok_contract, where = False, "## Design"
    for blob, label in (("\n".join(design or []), "## Design"), (text, "document")):
        for m in CONTRACT_RE.finditer(blob):
            params = []
            for p in m.group(1).split(","):
                p = p.strip().split(":")[0].split("=")[0].strip().strip("*`")
                if p and p != "self":
                    params.append(p)
            if params == CONTRACT_PARAMS:
                ok_contract, where = True, label
                break
        if ok_contract:
            break
    hint = "write exactly: create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult"
    if ok_contract and where != "## Design":
        rep.row("FAIL", "Design has create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult  (found outside ## Design)")
    else:
        rep.check(ok_contract, "Design has create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult", hint)
    cmap = "\n".join(find_section(secs, "Constraint mapping") or []).lower()
    cited = [p for p in POLICIES if p in cmap]
    rep.check(len(cited) >= 2, f"Constraint mapping cites {len(cited)} policies >= 2" + (f" ({', '.join(cited)})" if cited else ""),
              "map constraints to booking-policy / ux-messages / security-baseline")
    concerns = [l for l in content_lines(find_section(secs, "Areas of concern")) if re.search(r"owner|เจ้าของ", l, re.I)]
    rep.check(len(concerns) >= 2, f"Areas of concern {len(concerns)} >= 2 with owner", "each line: '- <issue> · owner: <role>'")
    dlog = find_section(secs, "Decision log")
    rep.check(dlog is not None and bool(content_lines(dlog)), "Decision log present", "add ## Decision log with at least one entry")
    if re.search(r"Status:\s*[`*]*\s*approved", text, re.I):
        rep.row("PASS", "Status: approved")
    else:
        rep.row("WARN", "Status: approved missing (PO signs with Approved-by at commit)")


def check_plan(path: str, rep: Report) -> None:
    lines = read_lines(path)
    text = "\n".join(lines)
    secs = sections(lines)
    missing = [s for s in PLAN_SECTIONS if find_section(secs, s) is None]
    rep.check(not missing, f"sections {4 - len(missing)}/4", "missing: " + ", ".join(f"## {m}" for m in missing))
    order = find_section(secs, "Order of work") or []
    item0 = any(re.match(r"^\s*(?:[-*]\s*)?(?:\*\*)?0\s*[.)]", l) for l in order)
    rep.check(item0, "item 0 present", "Order of work must start with '0. บันทึกแผนนี้ … แล้วหยุดรอคำสั่ง'")
    rep.check("create_recurring_booking" in text, "contract create_recurring_booking", "plan must use the architect_note.md API")
    proof = "\n".join(find_section(secs, "Proof") or [])
    rep.check(bool(re.search(r"python\s+-m\s+pytest", proof)), "Proof has python -m pytest", "add: python -m pytest")
    rep.check(bool(re.search(r"check\.py\s+RR\b", proof)), "Proof has check.py RR", "add: python ../cdg-acceptance/check.py RR")
    if len(lines) > 50:
        rep.row("WARN", f"lines {len(lines)} > 50 (a plan a reviewer can read in 2 minutes)")
    else:
        rep.row("PASS", f"lines {len(lines)} <= 50")


CHECKS = {"claude-md": check_claude_md, "intent": check_intent, "spec": check_spec, "plan": check_plan}


# ------------------------------------------------------------------ --stage d1
STAGES = [  # (name, marker file, pytest_min, fr1_min, rr_min, docs expected)
    ("d1-end", "tests/test_recurring.py", 18, 4, 6, ["CLAUDE.md", "intent/recurring-booking/intent.md",
                                                    "intent/recurring-booking/spec.md", "intent/recurring-booking/plan.md"]),
    ("d1-after-l4", "intent/recurring-booking/plan.md", 17, 4, 0, ["CLAUDE.md", "intent/recurring-booking/intent.md",
                                                                   "intent/recurring-booking/spec.md"]),
    ("d1-after-l3", "intent/recurring-booking/spec.md", 17, 4, 0, ["CLAUDE.md", "intent/recurring-booking/intent.md"]),
    ("d1-after-l2", "intent/recurring-booking/intent.md", 17, 4, 0, ["CLAUDE.md"]),
    ("d1-after-l1", "tests/test_fr1_overlap.py", 17, 4, 0, ["CLAUDE.md"]),
]


def detect_stage(repo: str):
    if not os.path.isdir(os.path.join(repo, "scripts")):
        return ("mw-start", 13, 2, 0, [])
    for name, marker, pmin, fmin, rmin, docs in STAGES:
        if os.path.exists(os.path.join(repo, marker)):
            return (name, pmin, fmin, rmin, docs)
    return ("d1-start", 13, 2, 0, [])


def pytest_counts(out: str) -> tuple[int, int]:
    passed = failed = 0
    for line in reversed(out.splitlines()):
        if re.search(r"\b(passed|failed|error|errors|no tests ran)\b", line) and re.search(r"\bin [\d.]+s", line):
            m = re.search(r"(\d+) passed", line)
            passed = int(m.group(1)) if m else 0
            failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|errors?)\b", line))
            return passed, failed
    return 0, 1


def enabled_hooks(repo: str) -> list[str]:
    path = os.path.join(repo, ".claude", "settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            settings = json.load(fh)
    except (OSError, ValueError):
        return []
    commands = []
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries or []:
            for h in entry.get("hooks", []) or []:
                commands.append(h.get("command", ""))
    names = []
    snip_dir = os.path.join(repo, ".claude", "hooks", "snippets")
    if os.path.isdir(snip_dir):
        for fn in sorted(os.listdir(snip_dir)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(snip_dir, fn), "r", encoding="utf-8-sig") as fh:
                    snip = json.load(fh)
            except (OSError, ValueError):
                continue
            if snip.get("hook", {}).get("command") in commands:
                names.append(snip.get("name", fn[:-5]))
    return names


def stage_d1(rep: Report) -> int:
    repo = repo_root()
    acc = acceptance_dir(repo)
    name, pmin, fmin, rmin, docs = detect_stage(repo)
    rep.row("INFO", f"state {name}")
    br = git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    st = git(["status", "--porcelain"], repo)
    if br.returncode == 0:
        dirty = [l for l in st.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
        rep.row("INFO", f"git: branch {br.stdout.decode().strip()} · " + ("clean" if not dirty else f"{len(dirty)} uncommitted change(s)"))
    py = venv_python(repo)
    code, out = run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=repo)
    passed, failed = pytest_counts(out)
    if "No module named pytest" in out:
        rep.check(False, f"pytest not installed (expect >= {pmin} passed)",
                  "python -m venv .venv · source .venv/Scripts/activate · python -m pip install -r requirements-dev.txt"
                  "  (offline: --no-index --find-links ../wheels)")
    else:
        rep.check(failed == 0 and passed >= pmin, f"pytest {passed} passed (expect >= {pmin})" + (f", {failed} failed" if failed else ""),
                  "run: python -m pytest")
    check_py = os.path.join(acc, "check.py")
    if not os.path.isfile(check_py):
        rep.row("FAIL", "../cdg-acceptance/check.py not found (keep the kit folders together)")
        rep.finish()
        return 2
    for suite, need, total in (("FR-1", fmin, 4), ("RR", rmin, 6)):
        code, out = run([py, check_py, suite, "--repo", repo], cwd=repo, timeout=120)
        m = re.search(r"ACCEPTANCE (\d+)/(\d+)", out)
        got = int(m.group(1)) if m else 0
        tot = int(m.group(2)) if m else total
        expect = f"{need}/{tot}" if need < tot else f"{tot}/{tot}"
        rep.check(got >= need, f"{suite} {got}/{tot} (expect {'>= ' if need < tot and need else ''}{expect})",
                  f"python ../cdg-acceptance/check.py {suite}")
    hooks = enabled_hooks(repo)
    if name == "d1-end" and "linkage" not in hooks:
        rep.row("WARN", f"hooks enabled: {hooks} (expect linkage: python scripts/hooks.py enable linkage)")
    else:
        rep.row("INFO", f"hooks enabled: {hooks}")
    for d in docs:
        if not os.path.isfile(os.path.join(repo, d)):
            rep.row("WARN", f"{d} missing at state {name}")
    return rep.finish()


# ------------------------------------------------------------------ --leaks
def glob_hit(path: str, patterns: list[str]) -> str | None:
    p = path.replace("\\", "/").lower()
    for pat in patterns:
        q = pat.lower()
        cands = [q]
        if q.startswith("**/"):
            cands.append(q[3:])
        for c in cands:
            if fnmatch.fnmatchcase(p, c):
                return pat
    return None


def ls_tree(ref: str, repo: str) -> list[str]:
    r = git(["ls-tree", "-r", "-z", "--name-only", ref], repo)
    return [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]


def worktree_files(repo: str) -> list[str]:
    r = git(["ls-files", "-z", "-c", "-o", "--exclude-standard"], repo)
    return [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]


def grep_ref(marker: str, ref: str, repo: str) -> list[str]:
    r = git(["grep", "-I", "-l", "-F", "-e", marker, ref, "--"], repo)
    if r.returncode not in (0, 1):
        return []
    out = []
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        out.append(line.split(":", 1)[1] if line.startswith(ref + ":") else line)
    return out


def grep_worktree(marker: str, repo: str, files: list[str]) -> list[str]:
    hits = []
    needle = marker.encode("utf-8")
    for f in files:
        full = os.path.join(repo, f)
        try:
            with open(full, "rb") as fh:
                data = fh.read(2_000_000)
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue  # binary, like git grep -I
        if needle in data:
            hits.append(f)
    return hits


def leaks(rep: Report, pristine: bool) -> int:
    repo = repo_root()
    acc = acceptance_dir(repo)
    rules_path = os.path.join(acc, "leaks.json")
    if not os.path.isfile(rules_path):
        rep.row("FAIL", "../cdg-acceptance/leaks.json not found (keep the kit folders together)")
        rep.finish()
        return 2
    try:
        with open(rules_path, "r", encoding="utf-8-sig") as fh:
            rules = json.load(fh)
    except ValueError as exc:
        rep.row("FAIL", f"leaks.json is not valid JSON: {exc}")
        rep.finish()
        return 2
    if git(["rev-parse", "--git-dir"], repo).returncode != 0:
        rep.row("FAIL", "not a git repository")
        rep.finish()
        return 2

    refs_out = git(["for-each-ref", "--format=%(refname)"], repo).stdout.decode("utf-8", "replace").split()
    allowed = [re.compile(p) for p in rules.get("allowed_refs", [])] + [re.compile(r"^refs/stash$")]
    bad = [r for r in refs_out if not any(a.search(r) for a in allowed)]
    for r in bad:
        rep.row("FAIL", f"ref {r} is not allowed in the learner repo")
    if not bad:
        rep.row("PASS", f"refs: {len(refs_out)} allowed")

    fpaths = rules.get("forbidden_paths", [])
    markers = rules.get("forbidden_markers", [])
    wt_files = worktree_files(repo)
    targets = [(r, ls_tree(r, repo)) for r in refs_out if not r.startswith("refs/stash")]
    targets.append(("working tree", wt_files))
    path_hits = 0
    for label, files in targets:
        for f in files:
            pat = glob_hit(f, fpaths)
            if pat:
                path_hits += 1
                rep.row("FAIL", f"forbidden file {f} in {label} (rule {pat})")
    marker_hits = 0
    for m in markers:
        for r in refs_out:
            if r.startswith("refs/stash"):
                continue
            for f in grep_ref(m, r, repo):
                marker_hits += 1
                rep.row("FAIL", f"marker \"{m}\" in {r}:{f}")
        for f in grep_worktree(m, repo, wt_files):
            marker_hits += 1
            rep.row("FAIL", f"marker \"{m}\" in working tree: {f}")
    if not path_hits:
        rep.row("PASS", f"no forbidden files in {len(targets) - 1} ref(s) + working tree")
    if not marker_hits:
        rep.row("PASS", f"no forbidden markers in {len(targets) - 1} ref(s) + working tree")

    mw = rules.get("mw_start", {})
    tag = "refs/tags/checkpoint/mw-start"
    if tag in refs_out:
        mw_hits = 0
        for f in ls_tree(tag, repo):
            pat = glob_hit(f, mw.get("forbidden_paths", []))
            if pat:
                mw_hits += 1
                rep.row("FAIL", f"mw-start has {f} (rule {pat})")
        for m in mw.get("forbidden_markers", []):
            for f in grep_ref(m, tag, repo):
                mw_hits += 1
                rep.row("FAIL", f"mw-start marker \"{m}\" in {f}")
        if not mw_hits:
            rep.row("PASS", "checkpoint/mw-start is stripped (mw_start rules)")
    else:
        rep.row("FAIL", "tag checkpoint/mw-start missing (re-extract the kit zip)")

    if pristine:
        shipped = str(rules.get("shipped_main_sha", ""))
        main_sha = git(["rev-parse", "-q", "--verify", "refs/heads/main"], repo).stdout.decode().strip()
        if not re.fullmatch(r"[0-9a-f]{7,40}", shipped):
            rep.row("WARN", "pristine rules skipped (shipped_main_sha not set: kit not built by make_kit)")
        elif not main_sha or not main_sha.startswith(shipped) and not shipped.startswith(main_sha):
            rep.row("INFO", "pristine rules skipped (main has moved since the kit was shipped)")
        else:
            pr = rules.get("pristine", {})
            p_hits = 0
            for label, files in (("main", ls_tree("refs/heads/main", repo)), ("working tree", wt_files)):
                for f in files:
                    pat = glob_hit(f, pr.get("forbidden_paths", []))
                    if pat:
                        p_hits += 1
                        rep.row("FAIL", f"pristine: {f} in {label} (rule {pat})")
            for m in pr.get("forbidden_markers", []):
                for f in grep_ref(m, "refs/heads/main", repo):
                    p_hits += 1
                    rep.row("FAIL", f"pristine marker \"{m}\" in main:{f}")
            if not p_hits:
                rep.row("PASS", "pristine rules (main == shipped kit)")
    return rep.finish()


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="doctor.py", description="Check lab documents, the Day-1 repo state, or kit leaks.")
    ap.add_argument("--check", nargs=2, metavar=("KIND", "FILE"), help="KIND = claude-md | intent | spec | plan")
    ap.add_argument("--stage", choices=["d1"], help="check the repo state for Day 1")
    ap.add_argument("--leaks", action="store_true", help="scan refs and files for answer leaks (uses ../cdg-acceptance/leaks.json)")
    ap.add_argument("--pristine", action="store_true", help="with --leaks: also apply the as-shipped rules while main is unchanged")
    args = ap.parse_args(argv)

    if args.check:
        kind, path = args.check
        if kind not in CHECKS:
            print(f"FAIL  unknown kind '{kind}' (use: {', '.join(CHECKS)})")
            return 2
        rep = Report(kind)
        if not os.path.isfile(path):
            rep.row("FAIL", f"file not found: {path.replace(chr(92), '/')}")
            rep.finish()
            return 2
        CHECKS[kind](path, rep)
        return rep.finish()
    if args.stage:
        return stage_d1(Report(args.stage))
    if args.leaks:
        return leaks(Report("leaks"), args.pristine)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
