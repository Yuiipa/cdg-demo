#!/usr/bin/env python
"""List and call the internal-tools MCP tools without Claude (Day 2, Lab 3).

Usage (from the repo root):
    python scripts/mcp_tools.py list [--trace]
    python scripts/mcp_tools.py call <tool> ['<json-args>']

Examples:
    python scripts/mcp_tools.py call get_ticket '{"ticket_id": "BOOK-188"}'
    python scripts/mcp_tools.py call list_incidents
    python scripts/mcp_tools.py call create_ticket '{"summary": "...", "description": "..."}'

Imports mcp_server/internal_tools/server.py in-process (the same code the MCP server runs),
so a new tool registered by day2_tools.py shows up here before Claude is restarted.
If day2_tools.py exists but cannot be imported, a WARN line names the error (--trace shows
the traceback). Anything printed to stdout while importing or calling a tool is reported
as a WARN too: stdout is the MCP stdio channel, a print there breaks the server.
Exit 0 = OK, 1 = day2_tools import failed / stdout leak (list) or the tool returned an
error (call), 2 = usage error, mcp package missing, or the server itself cannot import.
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.metadata
import io
import json
import os
import sys
import traceback

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.dont_write_bytecode = True  # no __pycache__ in mcp_server/ (same rule as run_server.py)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MCP_DIR = os.path.join(REPO, "mcp_server")
DAY2_FILE = os.path.join(MCP_DIR, "internal_tools", "day2_tools.py")
SERVER_NAME = "internal-tools"
PIP_HINT = "fix: python -m pip install -r requirements-mcp.txt"
LEAK_HINT = "stdout is the MCP channel: print to sys.stderr or remove the print"


class Capture:
    """Catch anything written to stdout while importing the server or calling a tool."""

    def __enter__(self):
        self._old = sys.stdout
        self.buf = io.StringIO()
        sys.stdout = self.buf
        return self

    def __exit__(self, *exc):
        sys.stdout = self._old
        return False

    @property
    def text(self) -> str:
        return self.buf.getvalue()


class Loaded:
    mcp = None
    day2_error: str | None = None
    day2_tb: str | None = None
    leak: str = ""
    fatal = False  # the server itself cannot import (mcp missing, broken server.py)


def mcp_version() -> str:
    try:
        return importlib.metadata.version("mcp")
    except Exception:
        return "?"


def short(text: str, n: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def import_server(trace: bool) -> Loaded:
    """Import internal_tools.server (which imports day2_tools when present); print WARN/FAIL lines."""
    out = Loaded()
    if MCP_DIR not in sys.path:
        sys.path.insert(0, MCP_DIR)
    try:
        with Capture() as cap:
            from internal_tools.server import mcp  # noqa: F401
    except Exception as exc:
        tb = traceback.format_exc()
        if "day2_tools" in tb:
            # an error other than ImportError inside day2_tools.py propagates through server.py
            out.day2_error = f"{type(exc).__name__}: {exc}"
            out.day2_tb = tb
            print(f"WARN  day2_tools: {out.day2_error}")
            print("      the server cannot start until this is fixed" + ("" if trace else " (python scripts/mcp_tools.py list --trace)"))
            if trace:
                print(tb.rstrip())
            out.fatal = True
            return out
        print(f"FAIL  cannot import internal_tools.server: {type(exc).__name__}: {exc}")
        print(f"      {PIP_HINT}")
        if trace:
            print(tb.rstrip())
        out.fatal = True
        return out
    out.mcp = mcp
    out.leak = cap.text
    if os.path.isfile(DAY2_FILE) and "internal_tools.day2_tools" not in sys.modules:
        # server.py swallows ImportError from day2_tools; import it again to show the reason
        try:
            with Capture() as cap2:
                importlib.import_module("internal_tools.day2_tools")
            out.leak += cap2.text
        except Exception as exc:
            out.day2_error = f"{exc}" if isinstance(exc, ImportError) else f"{type(exc).__name__}: {exc}"
            out.day2_tb = traceback.format_exc()
    if out.day2_error:
        print(f"WARN  day2_tools: {out.day2_error}")
        if trace and out.day2_tb:
            print(out.day2_tb.rstrip())
        else:
            print("      see the traceback: python scripts/mcp_tools.py list --trace")
    if out.leak:
        print(f"WARN  day2_tools: printed to stdout at import ({short(out.leak)!r}); {LEAK_HINT}")
    return out


def first_line(text: str | None) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def unwrap(res):
    """Turn a CallToolResult (mcp 2.x) or a 1.x return value into plain JSON data."""
    structured = getattr(res, "structured_content", None)
    if isinstance(structured, dict) and list(structured) == ["result"]:
        return structured["result"]
    if structured is not None:
        return structured
    content = getattr(res, "content", None)
    if content is None and isinstance(res, tuple) and len(res) == 2:  # mcp 1.x (content, structured)
        content, structured = res
        if structured is not None:
            return structured
    if content is None and isinstance(res, (list, dict, str, int, float, bool)):
        return res
    texts = [getattr(c, "text", None) for c in (content or []) if getattr(c, "text", None) is not None]
    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except ValueError:
            parsed.append(t)
    if len(parsed) == 1:
        return parsed[0]
    return parsed


def cmd_list(trace: bool) -> int:
    loaded = import_server(trace)
    if loaded.fatal:
        return 1 if loaded.day2_error else 2
    tools = asyncio.run(loaded.mcp.list_tools())
    name = getattr(loaded.mcp, "name", None) or SERVER_NAME
    print(f"MCP {name} · {len(tools)} tools (mcp {mcp_version()})")
    for t in tools:
        print(f"  {t.name:<22}{first_line(getattr(t, 'description', None))}")
    return 1 if (loaded.day2_error or loaded.leak) else 0


def cmd_call(tool: str, raw_args: str | None, trace: bool) -> int:
    args: dict = {}
    if raw_args is not None and raw_args.strip():
        try:
            args = json.loads(raw_args)
        except ValueError as exc:
            print(f"FAIL  args must be a JSON object, e.g. '{{\"ticket_id\": \"BOOK-188\"}}' ({exc})")
            return 2
        if not isinstance(args, dict):
            print("FAIL  args must be a JSON object (a {...} with the tool's parameters)")
            return 2
    loaded = import_server(trace)
    if loaded.fatal:
        return 1 if loaded.day2_error else 2
    names = [t.name for t in asyncio.run(loaded.mcp.list_tools())]
    if tool not in names:
        print(f"FAIL  unknown tool '{tool}' (available: {', '.join(names)})")
        return 2
    try:
        with Capture() as cap:
            res = asyncio.run(loaded.mcp.call_tool(tool, args))
    except Exception as exc:
        print(f"FAIL  {tool}: {short(str(exc), 300)}")
        if trace:
            print(traceback.format_exc().rstrip())
        return 1
    print(json.dumps(unwrap(res), ensure_ascii=False, indent=2))
    if cap.text:
        print(f"WARN  {tool}: printed to stdout during the call ({short(cap.text)!r}); {LEAK_HINT}")
        return 1
    return 1 if getattr(res, "is_error", False) else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    trace = "--trace" in argv
    argv = [a for a in argv if a != "--trace"]
    if not argv or argv[0] in ("-h", "--help"):
        print((__doc__ or "").strip())
        return 2
    cmd = argv[0]
    if cmd == "list":
        if len(argv) > 1:
            print("FAIL  usage: python scripts/mcp_tools.py list [--trace]")
            return 2
        return cmd_list(trace)
    if cmd == "call":
        if len(argv) < 2 or len(argv) > 3:
            print("FAIL  usage: python scripts/mcp_tools.py call <tool> ['<json-args>']")
            return 2
        return cmd_call(argv[1], argv[2] if len(argv) == 3 else None, trace)
    print(f"FAIL  unknown command '{cmd}' (use: list, call)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
