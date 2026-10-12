#!/usr/bin/env python
"""Start the internal-tools MCP server over stdio (used by `claude mcp add`).

Usage:
    python mcp_server/run_server.py [--repo <path>]     # --repo is accepted and ignored on Day 1

Puts its own folder on sys.path, so it works from any cwd and under `python -I`.
Register it with:  python scripts/setup_mcp.py
"""
from __future__ import annotations

import os
import sys

try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# no __pycache__ in mcp_server/: it would survive `git switch` to checkpoint/mw-start as an empty-looking folder
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def main(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        sys.stderr.write(__doc__ or "")
        return 0
    try:
        from internal_tools.server import mcp
    except ImportError as exc:
        sys.stderr.write(f"internal-tools: cannot start ({exc}). Fix: python -m pip install -r requirements-mcp.txt\n")
        return 2
    mcp.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
