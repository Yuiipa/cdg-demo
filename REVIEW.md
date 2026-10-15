# Review: feature/fr6-small-room เทียบกับ main
Branch: feature/fr6-small-room · Reviewer agent run by: Papawadee · วันที่: 2026-10-15 · Spec: intent/fr6-small-room-limit/spec.md

> กติกา: ตาราง Findings ต้องตรงกับที่ agent รายงาน ห้ามเพิ่มหรือตัด · คนเป็นผู้ตัดสิน (ช่อง triage และ Verdict ของคน) ไม่ใช่ agent · evidence ต้องชี้ file:line หรือผลคำสั่ง ไม่ใช่คำบอกเล่า

## Findings

| # | file:line | severity | issue | evidence | triage |
|---|---|---|---|---|---|
| 1 | - | - | ไม่พบ finding (no findings) | `git diff main...HEAD` มีแค่ `booking/service.py` (+7) และไฟล์ใหม่ `tests/test_fr6_small_room.py` (+64); `git diff --stat main -- tests/test_rules.py tests/test_service.py` ว่าง (ไม่แก้ test เดิม); constants `SMALL_ROOM_CAPACITY = 6` / `SMALL_ROOM_MAX_DURATION = timedelta(hours=2)` ที่ `booking/service.py:17-18` ใช้ใน `_check_duration` บรรทัด 144-148 ต่อจากกฎ FR-3 ที่บรรทัด 138-143 (ตรง R4); error code `SMALL_ROOM_TOO_LONG` และข้อความ `f"ห้อง {room.room_id} เป็นห้องเล็ก จองได้ครั้งละไม่เกิน 2 ชั่วโมง"` ตรง R2 คำต่อคำ มีแค่ `room.room_id` ไม่มีข้อมูลส่วนบุคคล (booking-policy §1) ตรง R6; R1 คุมโดย `test_fr6_small_room_two_hours_ok` (ขอบ 2 ชม. พอดีผ่าน); R2 โดย `test_fr6_small_room_too_long_rejected`; R3 โดย `test_fr6_large_room_uses_fr3_limit` (R101 3 ชม. ความจุ 20 ยังผ่าน ไม่กระทบ FR-3) และ `tests/test_rules.py` ของ FR-3 ผ่านทั้งหมดโดยไม่แก้; R4 โดย `test_fr6_checked_after_fr3_short_duration` (จอง 15 นาทีบนห้องเล็ก R102 ได้ `INVALID_DURATION` ไม่ใช่ `SMALL_ROOM_TOO_LONG`); R5 โดย `test_fr6_recurring_small_room_first_occurrence_rejected` (ครั้งแรกเกิน 2 ชม. บน R102 ผ่าน `create_recurring_booking` → `SMALL_ROOM_TOO_LONG` และ `list_bookings("R102")` ยังว่าง) | wontfix (ไม่มี finding ให้แก้) |

triage (Partner กรอก): `fix` = Driver แก้ในเทิร์นถัดไป · `wontfix` = ไม่แก้ บอกเหตุผลสั้น ๆ · `question` = ต้องถาม PO / QA ก่อน

## Verdict
- Agent: approve
- Human: approve โดย bambam (reviewer) · เหตุผล 1 บรรทัด: ตรง spec R1–R6, test เดิมไม่ถูกแตะ, ACCEPTANCE 6/6

## Tests
- `python -m pytest` (agent รายงาน): 28 passed in 0.05s
- `python -m pytest` (คนรันเองใน terminal 2): 28 passed in 0.03s
- `git diff --stat main -- tests/test_rules.py tests/test_service.py`: ว่าง
