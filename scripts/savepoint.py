"""Save points: ดึงงานที่ทำเสร็จแล้วของ lab ก่อนหน้าเข้ามา เมื่อตามไม่ทัน (offline, ไม่ใช้ network).

  python scripts/savepoint.py list
  python scripts/savepoint.py catchup <name> [--kit-wins] [--branch <new-branch>] [--dry-run]

Save point อยู่นอก repo ที่ ../cdg-acceptance/savepoints/day1.bundle (หรือ env CDG_ACCEPTANCE_DIR)
งานค้างจะถูกเก็บใน branch wip/<เวลา> ก่อนเสมอ · โค้ดและ test มาจาก kit · เอกสารที่คุณแก้เอง (CLAUDE.md, intent/) เป็นของคุณ
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
CODE_PREFIXES = ("booking/", "tests/", ".claude/", "scripts/", "mcp_server/")
CODE_FILES = ("pyproject.toml", "skills-lock.json")
SYNC_PREFIXES = ("booking/", "tests/")
DAY2_COMMANDS = ("day2", "after-mc", "fetch")
LEARNER_ID = ["-c", "user.name=CDG learner", "-c", "user.email=learner@cdg.example"]


class GitError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def acceptance_dir() -> Path:
    env = os.environ.get("CDG_ACCEPTANCE_DIR", "").strip()
    return Path(env) if env else REPO.parent / "cdg-acceptance"


def bundle_path() -> Path:
    return acceptance_dir() / "savepoints" / "day1.bundle"


def git(*args: str, check: bool = True, prefix: list[str] | None = None) -> str:
    cmd = ["git", *(prefix or []), *args]
    proc = subprocess.run(
        cmd, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git {' '.join(args)} -> exit {proc.returncode}: {err or out.strip()}")
    return out


def git_ok(*args: str) -> bool:
    proc = subprocess.run(["git", *args], cwd=str(REPO), stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return proc.returncode == 0


def identity_prefix() -> list[str]:
    name = git("config", "user.name", check=False).strip()
    email = git("config", "user.email", check=False).strip()
    return [] if (name and email) else list(LEARNER_ID)


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def branch_exists(name: str) -> bool:
    return git_ok("show-ref", "--verify", "--quiet", f"refs/heads/{name}")


def unique_branch(base: str) -> str:
    name, n = base, 2
    while branch_exists(name):
        name = f"{base}-{n}"
        n += 1
    return name


def load_manifest() -> dict:
    path = acceptance_dir() / "savepoints" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    items = data.get("savepoints", data) if isinstance(data, dict) else {}
    return {k: v for k, v in items.items() if isinstance(v, dict)}


def bundle_heads() -> set[str]:
    bundle = bundle_path()
    if not bundle.is_file():
        return set()
    out = git("bundle", "list-heads", bundle.as_posix(), check=False)
    heads = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("refs/tags/checkpoint/"):
            heads.add(parts[1][len("refs/tags/checkpoint/"):])
    return heads


def in_progress_operation() -> str | None:
    checks = [
        ("MERGE_HEAD", "git merge --abort"),
        ("CHERRY_PICK_HEAD", "git cherry-pick --abort"),
        ("REVERT_HEAD", "git revert --abort"),
        ("rebase-merge", "git rebase --abort"),
        ("rebase-apply", "git rebase --abort"),
    ]
    for name, fix in checks:
        rel = git("rev-parse", "--git-path", name, check=False).strip()
        if rel and (REPO / rel).exists():
            return fix
    return None


def split_z(out: str) -> list[str]:
    return [p for p in out.split("\0") if p]


def is_code_path(path: str) -> bool:
    if path in CODE_FILES or path.startswith(CODE_PREFIXES):
        return True
    return path.startswith("requirements") and path.endswith(".txt") and "/" not in path


# ---------------------------------------------------------------- commands
def cmd_list() -> int:
    manifest = load_manifest()
    heads = bundle_heads()
    if not bundle_path().is_file():
        print(f"FAIL  ไม่พบ {bundle_path().as_posix()} (วางโฟลเดอร์ cdg-acceptance ไว้ข้าง repo)")
        return 2
    print("name | lab | คำอธิบาย | available")
    names = list(manifest) or sorted(heads)
    for name in names:
        info = manifest.get(name, {})
        avail = "yes" if name in heads else "no"
        print(f"{name} | {info.get('lab', '-')} | {info.get('description_th', '-')} | {avail}")
    print("ใช้: python scripts/savepoint.py catchup <name>")
    return 0


def run_doctor() -> int:
    doctor = REPO / "scripts" / "doctor.py"
    if doctor.is_file():
        proc = subprocess.run([sys.executable, str(doctor), "--stage", "d1"], cwd=str(REPO),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        print(proc.stdout.decode("utf-8", errors="replace").rstrip())
        return proc.returncode
    # fallback: pytest only
    venv_py = REPO / ".venv" / "Scripts" / "python.exe"
    py = str(venv_py) if venv_py.is_file() else sys.executable
    proc = subprocess.run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=str(REPO),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    tail = proc.stdout.decode("utf-8", errors="replace").strip().splitlines()[-1:]
    print(f"INFO  doctor.py not found; pytest: {tail[0] if tail else '?'}")
    return 0 if proc.returncode == 0 else 1


def cmd_catchup(name: str, kit_wins: bool, new_branch: str | None, dry_run: bool) -> int:
    if not git_ok("rev-parse", "--git-dir"):
        print("FAIL  ไม่ใช่ git repo: รันจาก root ของ cdg-claude-code-demo")
        return 2
    fix = in_progress_operation()
    if fix:
        print("FAIL  มี merge/rebase/cherry-pick ค้างอยู่ ยกเลิกก่อนด้วย:")
        print(f"      {fix}")
        return 2
    bundle = bundle_path()
    if not bundle.is_file():
        print(f"FAIL  ไม่พบ {bundle.as_posix()} (วางโฟลเดอร์ cdg-acceptance ไว้ข้าง repo)")
        return 2
    heads = bundle_heads()
    if name not in heads:
        print(f"FAIL  ไม่รู้จัก save point '{name}' ที่มีให้:")
        cmd_list()
        return 2
    if not branch_exists("main"):
        print("FAIL  ไม่พบ branch main")
        return 2

    ident = identity_prefix()
    ts = stamp()
    current = git("symbolic-ref", "--short", "-q", "HEAD", check=False).strip()

    # 2. dirty tree -> wip/<ts>
    dirty = git("status", "--porcelain", "--untracked-files=all").strip()
    if dirty:
        wip = unique_branch(f"wip/{ts}")
        if dry_run:
            print(f"DRY   would save uncommitted work to {wip}")
        else:
            git("switch", "-c", wip)
            git("add", "-A")
            git("commit", "--no-verify", "-q", "-m", f"wip: before catch-up {name}", prefix=ident)
            print(f"WIP saved: {wip}")

    # 3. switch to main
    if not dry_run:
        git("switch", "-q", "main")
    if current and current != "main":
        print(f"INFO  your branch {current} is kept as is")

    # 4. fetch the save point (no tag is created)
    git("fetch", "-q", "--no-tags", bundle.as_posix(), f"refs/tags/checkpoint/{name}")
    kit_sha = git("rev-parse", "FETCH_HEAD^{commit}").strip()
    head_ref = "HEAD" if not dry_run else "main"

    merged = False
    if git_ok("merge-base", "--is-ancestor", kit_sha, head_ref):
        print("INFO  already up to date")
    else:
        base = git("merge-base", head_ref, kit_sha, check=False).strip()
        if not base:
            print("FAIL  save point ไม่มีประวัติร่วมกับ main (repo นี้มาจาก kit อื่น?) ให้ TA ช่วย")
            return 2
        kit_changes: list[tuple[str, str]] = []
        fields = split_z(git("diff", "--no-renames", "--name-status", "-z", base, kit_sha))
        for i in range(0, len(fields) - 1, 2):
            kit_changes.append((fields[i], fields[i + 1]))
        mine = set(split_z(git("diff", "--no-renames", "--name-only", "-z", base, head_ref)))

        plan: list[tuple[str, str, str]] = []  # (action, status, path)
        kit_paths = set()
        for status, path in kit_changes:
            kit_paths.add(path)
            if not is_code_path(path) and path in mine and not kit_wins:
                plan.append(("KEPT YOURS", status, path))
            else:
                plan.append(("FROM KIT", status, path))
        # booking/ and tests/ must equal the kit exactly, so the next lab's tests and
        # acceptance match (your own versions stay in history: main^1 and wip/)
        kit_tree = set(split_z(git("ls-tree", "-r", "-z", "--name-only", kit_sha)))
        for path in sorted(mine - kit_paths):
            if path.startswith(SYNC_PREFIXES):
                plan.append(("FROM KIT", "M", path) if path in kit_tree else ("REMOVED", "D", path))

        if dry_run:
            for action, status, path in plan:
                print(f"DRY   {action}  {path}")
            print("DRY   no changes made")
            return 0

        git("merge", "--no-ff", "--no-commit", "-s", "ours", kit_sha, prefix=ident)
        for action, status, path in plan:
            if action != "KEPT YOURS":
                if status.startswith("D"):
                    git("rm", "-q", "--ignore-unmatch", "--", path)
                else:
                    git("checkout", kit_sha, "--", path)
            note = "  (ของเดิมอยู่ใน history)" if action == "REMOVED" else ""
            print(f"{action}  {path}{note}")
        git("commit", "--no-verify", "-q", "-m", f"catch-up: {name}", "-m", "Catch-up: true", prefix=ident)
        short = git("rev-parse", "--short", "HEAD").strip()
        print(f"MERGED  {short}  Catch-up: true")
        merged = True

    # 9. --branch
    if new_branch:
        if dry_run:
            print(f"DRY   would create branch {new_branch} from main")
        else:
            if branch_exists(new_branch):
                old = unique_branch(f"wip/{new_branch}-{ts}")
                git("branch", "-m", new_branch, old)
                print(f"INFO  old {new_branch} renamed to {old}")
            git("switch", "-q", "-c", new_branch, "main")
            print(f"INFO  now on {new_branch} (from main)")

    if dry_run:
        return 0

    # 10. doctor
    rc = run_doctor()
    if rc == 0:
        print("SAVEPOINT: OK")
        return 0
    print("SAVEPOINT: MERGED, DOCTOR NOT GREEN" if merged else "SAVEPOINT: DOCTOR NOT GREEN")
    print("INFO  งานไม่หาย: ดูแถว FAIL ด้านบน (บอกวิธีแก้) · ไม่ต้องรัน catchup ซ้ำ · ยังไม่ได้: เรียก TA")
    return 1


def usage() -> int:
    print(__doc__.strip())
    return 2


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        return usage()
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "list":
            return cmd_list()
        if cmd == "catchup":
            name, kit_wins, new_branch, dry_run = None, False, None, False
            i = 0
            while i < len(rest):
                a = rest[i]
                if a == "--kit-wins":
                    kit_wins = True
                elif a == "--dry-run":
                    dry_run = True
                elif a == "--branch" and i + 1 < len(rest):
                    new_branch = rest[i + 1]
                    i += 1
                elif a.startswith("--branch="):
                    new_branch = a.split("=", 1)[1]
                elif not a.startswith("-") and name is None:
                    name = a
                else:
                    print(f"FAIL  unknown argument: {a}")
                    return usage()
                i += 1
            if not name:
                print("FAIL  ต้องระบุชื่อ save point")
                cmd_list()
                return 2
            return cmd_catchup(name, kit_wins, new_branch, dry_run)
        if cmd in DAY2_COMMANDS:
            # Day-2 extension point: reads savepoints/day2.bundle when it ships
            if not (acceptance_dir() / "savepoints" / "day2.bundle").is_file():
                print(f"FAIL  '{cmd}' is not in the Day 1 kit (ไฟล์วันที่ 2 จะมากับ kit วันพรุ่งนี้)")
                return 2
            print(f"FAIL  '{cmd}' needs the Day 2 version of savepoint.py: update the kit")
            return 2
        print(f"FAIL  unknown command: {cmd}")
        return usage()
    except GitError as exc:
        print(f"FAIL  {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
