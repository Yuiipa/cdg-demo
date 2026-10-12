#!/usr/bin/env python
"""Register the internal-tools MCP server with Claude Code (local scope) and verify it.

Usage (from the repo root):
    python scripts/setup_mcp.py                         # register + verify (claude mcp get)
    python scripts/setup_mcp.py --test                  # start the server directly, no Claude
    python scripts/setup_mcp.py --remove                # unregister
    python scripts/setup_mcp.py --print-config <out.json>   # write an mcpServers JSON (Day-2 extension)

Registration uses local scope (~/.claude.json, keyed by this folder), so no .mcp.json
with machine paths lands in the repo. The server runs with the repo's .venv python.
Exit: 0 = connected / test passed, 1 = registered but not connected / test failed,
2 = claude CLI missing, mcp package missing, or other environment error.
If MCP does not work in class: python scripts/roles.py reveal ticket  (ticket as a file).
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NAME = "internal-tools"
SERVER = os.path.join(REPO, "mcp_server", "run_server.py")
FALLBACK = "INFO  fallback: python scripts/roles.py reveal ticket  แล้ว /intent-interview intent/sources/recurring/BOOK-142.md"


def fwd(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/")


def venv_python() -> tuple[str, bool]:
    for cand in (os.path.join(REPO, ".venv", "Scripts", "python.exe"), os.path.join(REPO, ".venv", "bin", "python")):
        if os.path.isfile(cand):
            return cand, True
    return sys.executable, False


def claude_cmd() -> list[str] | None:
    path = shutil.which("claude")
    if not path:
        return None
    if path.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", path]
    return [path]


def run_claude(base: list[str], args: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(base + args, cwd=REPO, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except OSError as exc:
        return 127, str(exc)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def mcp_importable(py: str) -> tuple[bool, str]:
    try:
        p = subprocess.run([py, "-c", "import mcp, importlib.metadata as m; print(m.version('mcp'))"],
                           capture_output=True, timeout=60, cwd=REPO)
    except Exception as exc:
        return False, str(exc)
    out = (p.stdout or p.stderr).decode("utf-8", "replace").strip()
    return p.returncode == 0, out.splitlines()[-1] if out else ""


# ------------------------------------------------------------------ --test (raw JSON-RPC over stdio)
def stdio_test(py: str, timeout: float = 20.0) -> tuple[bool, str]:
    if not os.path.isfile(SERVER):
        return False, "mcp_server/run_server.py not found (are you on main?)"
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.Popen([py, SERVER, "--repo", fwd(REPO)], cwd=REPO, env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        return False, f"cannot start server: {exc}"
    lines: queue.Queue = queue.Queue()
    errs: list[bytes] = []

    def pump_out():
        for raw in iter(proc.stdout.readline, b""):
            lines.put(raw)
        lines.put(None)

    def pump_err():
        for raw in iter(proc.stderr.readline, b""):
            errs.append(raw)

    threading.Thread(target=pump_out, daemon=True).start()
    threading.Thread(target=pump_err, daemon=True).start()
    deadline = time.monotonic() + timeout

    def send(obj: dict) -> None:
        proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        proc.stdin.flush()

    def wait_for(msg_id: int) -> dict | None:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            try:
                raw = lines.get(timeout=left)
            except queue.Empty:
                return None
            if raw is None:
                return None
            try:
                msg = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("id") == msg_id:
                return msg

    def stderr_tail() -> str:
        text = b"".join(errs).decode("utf-8", "replace").strip().splitlines()
        return text[-1] if text else ""

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "setup_mcp", "version": "1.0"}}})
        init = wait_for(1)
        if init is None or "result" not in init:
            time.sleep(0.3)
            return False, "no initialize response" + (f": {stderr_tail()}" if stderr_tail() else "")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        res = wait_for(2)
        if res is None or "result" not in res:
            return False, "no tools/list response" + (f": {stderr_tail()}" if stderr_tail() else "")
        names = sorted(t.get("name", "?") for t in res["result"].get("tools", []))
        return True, f"{len(names)} tools: {', '.join(names)}"
    except (BrokenPipeError, OSError) as exc:
        time.sleep(0.3)
        return False, f"server exited ({exc})" + (f": {stderr_tail()}" if stderr_tail() else "")
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


# ------------------------------------------------------------------ commands
def cmd_test() -> int:
    py, in_venv = venv_python()
    if not in_venv:
        print(f"WARN  .venv not found; using {fwd(py)}")
    ok, ver = mcp_importable(py)
    if not ok:
        print(f"FAIL  import mcp failed in {fwd(py)}: {ver}")
        print("      fix: python -m pip install -r requirements-mcp.txt")
        return 2
    ok, detail = stdio_test(py)
    print(f"MCP test: {detail}")
    if not ok:
        print(FALLBACK)
    return 0 if ok else 1


def cmd_register() -> int:
    base = claude_cmd()
    if base is None:
        print("FAIL  claude CLI not found on PATH (open a new terminal, or install Claude Code)")
        print(FALLBACK)
        return 2
    py, in_venv = venv_python()
    if not in_venv:
        print("FAIL  .venv/Scripts/python.exe not found. Fix: python -m venv .venv  (in the repo root)")
        return 2
    ok, ver = mcp_importable(py)
    if not ok:
        print(f"FAIL  import mcp failed in .venv: {ver}")
        print("      fix: python -m pip install -r requirements-mcp.txt")
        print(FALLBACK)
        return 2
    print(f"PASS  mcp {ver} in .venv")
    ok, detail = stdio_test(py)
    print(f"{'PASS' if ok else 'FAIL'}  server starts: {detail}")
    if not ok:
        print(FALLBACK)
        return 1
    run_claude(base, ["mcp", "remove", NAME, "--scope", "local"], timeout=60)
    code, out = run_claude(base, ["mcp", "add", "--scope", "local", NAME, "--",
                                  fwd(py), fwd(SERVER), "--repo", fwd(REPO)], timeout=60)
    if code != 0:
        print(f"FAIL  claude mcp add: {out.strip().splitlines()[-1] if out.strip() else code}")
        print(FALLBACK)
        return 1
    print(f"INFO  registered {NAME} (scope local) -> {fwd(py)} mcp_server/run_server.py")
    code, out = run_claude(base, ["mcp", "get", NAME], timeout=60)
    if "Connected" in out and "Failed" not in out:
        print(f"MCP: {NAME} Connected")
        return 0
    status = next((l.strip() for l in out.splitlines() if "Status" in l), out.strip().splitlines()[-1] if out.strip() else "")
    if status:
        print(f"INFO  claude mcp get: {status}")
    print("MCP: registered but NOT connected")
    print(FALLBACK)
    return 1


def cmd_remove() -> int:
    base = claude_cmd()
    if base is None:
        print("FAIL  claude CLI not found on PATH")
        return 2
    code, out = run_claude(base, ["mcp", "remove", NAME, "--scope", "local"], timeout=60)
    print(f"REMOVED {NAME}" if code == 0 else f"INFO  {NAME} was not registered (local scope)")
    return 0


def cmd_print_config(out_path: str) -> int:
    py, in_venv = venv_python()
    cfg = {"mcpServers": {NAME: {"type": "stdio", "command": fwd(py), "args": [fwd(SERVER), "--repo", fwd(REPO)]}}}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out_path.replace(chr(92), '/')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="setup_mcp.py", description="Register / test the internal-tools MCP server.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--test", action="store_true", help="start the server directly and list its tools (no Claude)")
    g.add_argument("--remove", action="store_true", help="unregister internal-tools (local scope)")
    g.add_argument("--print-config", metavar="OUT_JSON", help="write an mcpServers config file")
    args = ap.parse_args(argv)
    if args.test:
        return cmd_test()
    if args.remove:
        return cmd_remove()
    if args.print_config:
        return cmd_print_config(args.print_config)
    return cmd_register()


if __name__ == "__main__":
    sys.exit(main())
