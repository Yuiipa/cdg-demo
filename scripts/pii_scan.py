#!/usr/bin/env python
"""Scan text files for personal data before they go into git or into a prompt.

Usage:
    python scripts/pii_scan.py <file-or-dir> [<file-or-dir> ...]

Detects: Thai mobile numbers, e-mail addresses, Thai national ID numbers (13 digits),
and a Thai honorific (คุณ / นาย / นางสาว / นาง) followed by a name.
Directories are scanned recursively for .md, .txt and .csv files.
Lines starting with "Author:" are ignored.

Output: one line per hit  "path:line: <type> <masked>"  then  "PII: none" (exit 0)
or "PII: N hit(s)" (exit 1). A missing file gives exit 2.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCAN_EXT = {".md", ".txt", ".csv"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}

THAI_ID_RE = re.compile(r"(?<![\d-])(\d-\d{4}-\d{5}-\d{2}-\d|\d{13})(?![\d])")
PHONE_RE = re.compile(r"(?<!\d)0[689]\d[-\s]?\d{3}[-\s]?\d{4}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}", re.IGNORECASE)

# Thai letters/marks that can make up a word (no digits, no ฯ/ๆ punctuation)
THAI_WORD = "[ก-ฮะ-ฺเ-๎]+"
HONORIFIC_RE = re.compile(
    r"(?<!ขอบ)(?<!พระ)(?<!บุญ)(?<!ทรง)(?<!เจ้า)(?<!ท)"
    r"(นางสาว|นาง|นาย|คุณ) ?(" + THAI_WORD + ")"
)

# words that start with the honorific but are not a person (e.g. คุณภาพ = quality)
NOT_NAME = {
    "คุณ": ("ภาพ", "สมบัติ", "ค่า", "ลักษณะ", "ประโยชน์", "ธรรม", "วุฒิ", "ูปการ", "ๆ"),
    "นาย": ("จ้าง", "หน้า", "ทุน", "ทะเบียน", "อำเภอ", "ช่าง", "ทหาร", "ประตู", "สถานี", "ตำรวจ",
            "กรัฐมนตรี", "กเทศมนตรี", "กสมาคม", "กองค์การ", "กอบต"),
    "นาง": ("แบบ", "พยาบาล", "ฟ้า", "งาม", "เอก", "ร้าย", "ใน"),
    "นางสาว": (),
}
# "you + verb": the word after คุณ is a verb or particle, so คุณ means "you"
YOU_VERBS = (
    "ต้อง", "จะ", "สามารถ", "ได้", "ไม่", "ควร", "ก็", "เป็น", "มี", "ช่วย", "อยาก", "เคย", "ทำ",
    "ใช้", "จอง", "เลือก", "ดู", "คือ", "กับ", "และ", "หรือ", "ที่", "ซึ่ง", "เอง", "ว่า", "เห็น",
    "คิด", "รู้", "อ่าน", "เขียน", "ส่ง", "รับ", "ถาม", "ตอบ", "บอก", "แก้", "ลอง", "รัน", "กด",
    "พิมพ์", "เปิด", "ปิด", "ยัง", "เพิ่ง", "กำลัง", "อาจ", "คง", "ค่ะ", "ครับ", "คะ", "นะ", "ทั้ง",
    "ขอ", "หา", "ต่อ", "ลืม", "เข้าใจ", "ต้องการ", "ให้",
)
AUTHOR_RE = re.compile(r"^\s*(?:[-*>]\s*)?(?:\*\*)?Author\s*:", re.IGNORECASE)


def mask_digits(text: str, keep_head: int, keep_tail: int) -> str:
    digits = [i for i, ch in enumerate(text) if ch.isdigit()]
    keep = set(digits[:keep_head]) | set(digits[-keep_tail:] if keep_tail else [])
    return "".join(ch if (not ch.isdigit() or i in keep) else "x" for i, ch in enumerate(text))


def mask_email(text: str) -> str:
    local, _, domain = text.partition("@")
    return (local[:1] + "***@" + domain) if local else "***@" + domain


def is_name(honorific: str, token: str) -> bool:
    if any(token.startswith(w) for w in NOT_NAME.get(honorific, ())):
        return False
    if honorific == "นาย" and token == "ก":
        return False
    if honorific == "คุณ" and any(token.startswith(v) for v in YOU_VERBS):
        return False
    return len(token) >= 2


def scan_line(line: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    taken: list[tuple[int, int]] = []

    def free(span: tuple[int, int]) -> bool:
        return all(span[1] <= a or span[0] >= b for a, b in taken)

    for m in THAI_ID_RE.finditer(line):
        taken.append(m.span())
        hits.append(("thai-id", mask_digits(m.group(0), 1, 1)))
    for m in PHONE_RE.finditer(line):
        if free(m.span()):
            taken.append(m.span())
            hits.append(("phone", mask_digits(m.group(0), 2, 3)))
    for m in EMAIL_RE.finditer(line):
        if free(m.span()):
            taken.append(m.span())
            hits.append(("email", mask_email(m.group(0))))
    for m in HONORIFIC_RE.finditer(line):
        hon, token = m.group(1), m.group(2)
        if is_name(hon, token):
            hits.append(("name", f"{hon}{token[:1]}***"))
    return hits


def iter_files(target: str):
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() in SCAN_EXT:
                yield os.path.join(root, fn)


def display(path: str) -> str:
    ap = os.path.abspath(path)
    try:
        rel = os.path.relpath(ap, os.getcwd())
        if not rel.startswith(".."):
            ap = rel
    except ValueError:
        pass
    return ap.replace("\\", "/")


def scan_file(path: str) -> list[str]:
    out = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        for no, line in enumerate(fh, 1):
            if AUTHOR_RE.match(line):
                continue
            for kind, masked in scan_line(line):
                out.append(f"{display(path)}:{no}: {kind} {masked}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pii_scan.py",
        description="Find phone numbers, e-mails, Thai IDs and honorific+name in .md/.txt/.csv files.",
    )
    ap.add_argument("paths", nargs="+", help="files or folders to scan")
    args = ap.parse_args(argv)

    missing = [p for p in args.paths if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"FAIL  file not found: {p.replace(chr(92), '/')}")
        print("PII: ERROR (file not found)")
        return 2

    lines: list[str] = []
    for target in args.paths:
        for path in iter_files(target):
            lines.extend(scan_file(path))
    for line in lines:
        print(line)
    if lines:
        print(f"PII: {len(lines)} hit(s)")
        return 1
    print("PII: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
