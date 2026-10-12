#!/usr/bin/env python
"""Audit trail: who decided what, read from git commit trailers.

Usage:
    python scripts/audit.py                 # whole history of HEAD
    python scripts/audit.py intent/         # only commits that touch a path
    python scripts/audit.py --last 3        # the 3 newest rows
    python scripts/audit.py --sha           # add a short-sha column

Columns: subject · Refs · signer (Accepted-by / Approved-by / Catch-up trailers).
Merge commits are hidden unless they carry a "Catch-up:" trailer.
Exit 0; exit 2 outside a git repo.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FMT = (
    "%h%x1f%P%x1f%s%x1f"
    "%(trailers:key=Refs,valueonly,separator=%x2C)%x1f"
    "%(trailers:key=Accepted-by,valueonly,separator=%x2C)%x1f"
    "%(trailers:key=Approved-by,valueonly,separator=%x2C)%x1f"
    "%(trailers:key=Catch-up,valueonly)%x1e"
)
SUBJ_W, REFS_W = 29, 13


def git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "i18n.logOutputEncoding=UTF-8", "-c", "core.quotepath=false", *args],
        capture_output=True,
    )


def fit(text: str, width: int) -> str:
    """Pad to width; if too long keep width-3 chars + … so 2 spaces always separate columns."""
    if len(text) > width - 2:
        text = text[: width - 3] + "…"
    return text.ljust(width)


def clean(value: str) -> str:
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return ", ".join(p for p in parts if p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audit.py", description="Show the decision trail (Refs / Accepted-by / Approved-by) from git.")
    ap.add_argument("path", nargs="?", help="only commits touching this path (e.g. intent/)")
    ap.add_argument("--last", type=int, metavar="N", help="show only the N newest rows")
    ap.add_argument("--sha", action="store_true", help="add a short-sha column")
    args = ap.parse_args(argv)

    probe = git(["rev-parse", "--git-dir"])
    if probe.returncode != 0:
        print("FAIL  not a git repository (run from cdg-claude-code-demo/)")
        return 2
    cmd = ["log", "--format=" + FMT]
    if args.path:
        cmd += ["--", args.path]
    res = git(cmd)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace").strip()
        if "does not have any commits" in err:
            print("INFO  no commits yet")
            return 0
        print(f"FAIL  git log failed: {err.splitlines()[0] if err else res.returncode}")
        return 2

    rows = []
    for rec in res.stdout.decode("utf-8", "replace").split("\x1e"):
        rec = rec.strip("\r\n")
        if not rec.strip():
            continue
        f = rec.split("\x1f")
        if len(f) < 7:
            continue
        sha, parents, subject = f[0].strip(), f[1].split(), f[2]
        refs, accepted, approved, catchup = (clean(x) for x in f[3:7])
        if len(parents) > 1 and not catchup:
            continue
        signer = []
        if accepted:
            signer.append(f"Accepted: {accepted}")
        if approved:
            signer.append(f"Approved: {approved}")
        if catchup:
            signer.append(f"Catch-up: {catchup}")
        who = " · ".join(signer)
        if not who and not refs:
            who = "(ไม่มี Refs)"
        rows.append((sha, subject, refs, who))
        if args.last and len(rows) >= args.last:
            break

    head = ("sha      " if args.sha else "") + f"{'subject':<{SUBJ_W}}{'Refs':<{REFS_W}}ผู้ลงชื่อ (trailer)"
    print(head)
    for sha, subject, refs, who in rows:
        refs_col = refs.ljust(REFS_W) if len(refs) < REFS_W else refs + " "
        line = (f"{sha:<9}" if args.sha else "") + fit(subject, SUBJ_W) + refs_col + who
        print(line.rstrip())
    if not rows:
        print("INFO  no commits" + (f" touching {args.path}" if args.path else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
