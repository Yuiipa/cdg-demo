#!/usr/bin/env python
"""Convert a Word .docx file to Markdown (stdlib only, no pandoc needed).

Usage:
    python scripts/docx2md.py <file.docx>                 # Markdown to stdout (UTF-8)
    python scripts/docx2md.py <file.docx> --out <file.md> # write a UTF-8 file

Headings (Title, Heading 1-3) become #/##/###, list paragraphs become "- ",
tables become GitHub Markdown tables, and paragraphs that are bold as a whole
become **bold** lines. Works under `python -I`, in Git Bash and in PowerShell.
Exit 0 = OK, 2 = file missing or not a .docx.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _val(el, tag):
    if el is None:
        return None
    child = el.find(W + tag)
    return None if child is None else child.get(W + "val")


def load_styles(zf: zipfile.ZipFile) -> dict[str, dict]:
    """styleId -> {name, list, level}"""
    styles: dict[str, dict] = {}
    try:
        root = ET.fromstring(zf.read("word/styles.xml"))
    except (KeyError, ET.ParseError):
        return styles
    for st in root.iter(W + "style"):
        sid = st.get(W + "styleId") or ""
        name = (_val(st, "name") or sid).lower()
        ppr = st.find(W + "pPr")
        has_num = ppr is not None and ppr.find(W + "numPr") is not None
        outline = _val(ppr, "outlineLvl") if ppr is not None else None
        styles[sid] = {"name": name, "list": has_num or name.startswith("list"), "outline": outline}
    return styles


def heading_level(style: dict | None, ppr) -> int:
    name = (style or {}).get("name", "")
    if name == "title":
        return 1
    m = re.match(r"heading\s*(\d)", name)
    if m:
        return min(int(m.group(1)), 3)
    outline = _val(ppr, "outlineLvl") if ppr is not None else None
    if outline is None and style:
        outline = style.get("outline")
    if outline is not None and outline.isdigit() and int(outline) < 9:
        return min(int(outline) + 1, 3)
    return 0


def run_text(run) -> tuple[str, bool]:
    parts = []
    for node in run:
        tag = node.tag
        if tag == W + "t":
            parts.append(node.text or "")
        elif tag == W + "tab":
            parts.append(" ")
        elif tag in (W + "br", W + "cr"):
            parts.append("\n")
        elif tag == W + "noBreakHyphen":
            parts.append("-")
    rpr = run.find(W + "rPr")
    bold = False
    if rpr is not None:
        b = rpr.find(W + "b")
        bold = b is not None and (b.get(W + "val") in (None, "1", "true", "on"))
    return "".join(parts), bold


def para_text(p) -> tuple[str, bool]:
    """Text of a paragraph (runs joined, incl. hyperlinks / insertions) and whether all of it is bold."""
    texts, all_bold, any_text = [], True, False
    for run in p.iter(W + "r"):
        # skip runs inside deleted text
        txt, bold = run_text(run)
        if txt.strip():
            any_text = True
            all_bold = all_bold and bold
        texts.append(txt)
    text = "".join(texts)
    text = re.sub(r"[  ]+", " ", text).strip()
    return text, (all_bold and any_text)


def cell_text(tc, styles) -> str:
    lines = []
    for p in tc.iter(W + "p"):
        t, _ = para_text(p)
        if t:
            lines.append(t.replace("\n", " "))
    return " <br> ".join(lines).replace("|", "\\|")


def table_md(tbl, styles) -> list[str]:
    rows = []
    for tr in tbl.findall(W + "tr"):
        rows.append([cell_text(tc, styles) for tc in tr.findall(W + "tc")])
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return out


def para_md(p, styles) -> str:
    ppr = p.find(W + "pPr")
    sid = _val(ppr, "pStyle") if ppr is not None else None
    style = styles.get(sid or "", None)
    text, all_bold = para_text(p)
    if not text:
        return ""
    level = heading_level(style, ppr)
    if level:
        return "#" * level + " " + text.replace("\n", " ")
    is_list = (ppr is not None and ppr.find(W + "numPr") is not None) or bool(style and style.get("list"))
    if is_list:
        return "- " + text.replace("\n", " ")
    if all_bold:
        return "**" + text.replace("\n", " ") + "**"
    return text


def walk(container, styles, out: list[str]) -> None:
    for child in container:
        tag = child.tag
        if tag == W + "p":
            line = para_md(child, styles)
            if line:
                out.append(line)
            else:
                out.append("")
        elif tag == W + "tbl":
            out.append("")
            out.extend(table_md(child, styles))
            out.append("")
        elif tag in (W + "sdt", W + "sdtContent", W + "customXml", W + "smartTag"):
            walk(child, styles, out)


def convert(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        styles = load_styles(zf)
        root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find(W + "body")
    out: list[str] = []
    walk(body if body is not None else root, styles, out)
    # collapse empty paragraphs; blank line between blocks
    blocks: list[str] = []
    for line in out:
        if line == "":
            if blocks and blocks[-1] != "":
                blocks.append("")
            continue
        if blocks and blocks[-1] != "":
            prev, cur = blocks[-1], line
            same_list = prev.startswith("- ") and cur.startswith("- ")
            same_table = prev.startswith("|") and cur.startswith("|")
            if not (same_list or same_table):
                blocks.append("")
        blocks.append(line)
    while blocks and blocks[-1] == "":
        blocks.pop()
    return "\n".join(blocks) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="docx2md.py", description="Convert .docx to Markdown (UTF-8).")
    ap.add_argument("docx", help="input .docx file")
    ap.add_argument("--out", help="write Markdown to this file instead of stdout")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.docx):
        print(f"FAIL  file not found: {args.docx.replace(chr(92), '/')}", file=sys.stderr)
        return 2
    if not zipfile.is_zipfile(args.docx):
        print(f"FAIL  not a .docx file: {args.docx.replace(chr(92), '/')}", file=sys.stderr)
        return 2
    try:
        md = convert(args.docx)
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f"FAIL  not a valid .docx ({type(exc).__name__}): {args.docx.replace(chr(92), '/')}", file=sys.stderr)
        return 2
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
        print(f"wrote {args.out.replace(chr(92), '/')}")
    else:
        sys.stdout.write(md)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
