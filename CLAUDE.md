# CLAUDE.md

ระบบจองห้องประชุม (Python 3.11 + pytest) · business rules อยู่ใน docs/spec_meeting_room_booking.docx (SPEC-BK-002)

## Commands
- Setup (Git Bash): `python -m venv .venv` → `source .venv/Scripts/activate` → `python -m pip install -r requirements-dev.txt`
- Test: python -m pytest   (ผลปกติ: "N passed")
- Read spec: python scripts/docx2md.py <file.docx>
- PII: python scripts/pii_scan.py <file>
- รันทีละคำสั่ง ไม่ต่อด้วย pipe, `;` หรือ `cd … &&` (allow rule จับเฉพาะคำสั่งเดี่ยว)

## Conventions
- แก้ไฟล์ด้วย Edit/Write ห้าม shell redirect (>, >>, tee)
- ทุก rule ที่ผิดต้อง raise `BookingError(code, message)`: code เป็นภาษาอังกฤษตัวพิมพ์ใหญ่ message เป็นภาษาไทย
- เวลาเป็น naive datetime เวลาไทย · เวลา "ตอนนี้" มาจาก `clock` ที่ฉีดเข้า `BookingService` ห้ามเรียก `datetime.now()` ตรง ๆ
- เก็บแค่ `user_id` ของผู้จอง ห้ามเก็บหรือแสดงชื่อ อีเมล เบอร์โทร
- ห้ามเพิ่ม dependency โดยไม่ถาม · commit ต้องมี trailer `Refs: <ticket>`

## Architecture
- `booking/service.py` คือที่อยู่ของกฎทั้งหมด (FR-1..FR-5) · `models.py` dataclass ล้วน · `storage.py` in-memory
- test ใช้ fixture ห้อง R101 (20 ที่) และ R102 (6 ที่) และตรึงเวลาไว้ที่ จันทร์ 2026-10-05 09:00
- เอกสารงาน (intent/spec/plan) อยู่ใต้ `intent/<topic>/` · template อยู่ใน `intent/TEMPLATES/`

## Things Claude gets wrong
- ห้ามแก้หรือลบ test เดิม ถ้า test เดิมขัดกับงาน ให้หยุดแล้วเขียน artifacts/escalation.md
- การจองที่ชนขอบ (จบ 11:00 / เริ่ม 11:00) ไม่ถือว่าซ้อน และการจองที่ยกเลิกแล้วไม่นับ
- สรุปว่า "test ผ่าน" โดยไม่ได้รันจริง: ต้องแปะบรรทัด `N passed` ดิบเสมอ

## Verifying your work
- Test: python -m pytest (all green: ต้องเห็น "N passed";
  never skip or delete a failing test)
Run the tests before reporting any task complete, and paste the output.
If a test fails, fix the code, not the test.
If a requirement conflicts with an existing test, don't change the test:
write artifacts/escalation.md and stop.
