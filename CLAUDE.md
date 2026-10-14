# CLAUDE.md

## Commands
- Test: `python -m pytest` (ผลปกติ: "N passed")
- Read spec: `python scripts/docx2md.py <file.docx>`
- PII: `python scripts/pii_scan.py <file>`

## Conventions
- แก้ไฟล์ด้วย Edit/Write เท่านั้น ห้าม shell redirect (`>`, `>>`, `tee`)
- Python 3.11+ ไฟล์ข้อความเป็น UTF-8 ขึ้นบรรทัดแบบ LF
- ทุก terminal ใหม่ต้อง `source .venv/Scripts/activate` ก่อนรัน test (ต้องเห็น `(.venv)`
  หน้า prompt) ถ้าใช้ PowerShell ให้รัน `.venv\Scripts\python.exe -m pytest` แทน
- `tests/test_rules.py`, `tests/test_service.py`, และไฟล์ใน `.claude/` ถูก hook
  `protect_files.py` ป้องกันการแก้ไว้แล้ว

## Architecture
- `booking/service.py` คือ business logic ทั้งหมด (`BookingService`, `BookingError`
  พร้อม error code) ตาม requirement ใน `docs/spec_meeting_room_booking.docx`
- `booking/storage.py` คือ `InMemoryRepository` ไม่มี DB จริง ข้อมูลหายเมื่อ process จบ
- `mcp_server/` คือ MCP server แยกสำหรับ internal tools ไม่ใช่ส่วนของ booking service

## Things Claude gets wrong
- ห้ามแก้หรือลบ test เดิม ถ้า test เดิมขัดกับงานที่ขอ ให้หยุดแล้วเขียน
  `artifacts/escalation.md` อธิบายความขัดแย้งแทน
- การจองที่ชนกันแค่ขอบเวลา (เช่น จบ 11:00 กับเริ่ม 11:00) ไม่ถือว่าซ้อนกัน และ
  การจองที่ถูกยกเลิกแล้ว (`status == "CANCELLED"`) ไม่ต้องเอามานับว่าซ้อน

## Verifying your work
- Test: `python -m pytest` (all green: ต้องเห็น "N passed"; never skip or delete a
  failing test)
- Run the tests before reporting any task complete, and paste the output.
- If a test fails, fix the code, not the test.
- If a requirement conflicts with an existing test, don't change the test: write
  `artifacts/escalation.md` and stop.
