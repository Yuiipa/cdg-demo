# Plan: จองห้องประชุมซ้ำรายสัปดาห์ (BOOK-142)

Spec: intent/recurring-booking/spec.md (approved) · Contract: intent/sources/recurring/architect_note.md

## Files that change
- `booking/models.py`: `Booking.series_id`, dataclass `RecurringResult`, `SkippedOccurrence`
- `booking/service.py`: `create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult`
- `booking/__init__.py`: export `RecurringResult`, `SkippedOccurrence`
- `tests/test_recurring.py` (ใหม่) · test เดิมไม่แตะ

## Order of work
0. บันทึกแผนนี้เป็น intent/recurring-booking/plan.md ตาม template แล้วหยุดรอคำสั่ง ห้ามแก้ไฟล์อื่น
1. `tests/test_recurring.py` ตาม R1–R7 ของ spec รันแล้วต้อง red ก่อน
2. `models.py`: `series_id: str | None = None` + `RecurringResult(created, skipped)` + `SkippedOccurrence(start, code, message)`
3. `service.py`: ตรวจ `weeks` (1..4, เกิน → `RECURRENCE_TOO_LONG`) → ตรวจครั้งแรกด้วยกฎเดิม → วนทีละ 7 วัน
4. ครั้งที่ชน (FR-1) → skipped `BOOKING_OVERLAP` · เกิน 30 วัน → skipped `BEYOND_HORIZON`
5. ข้อความ skipped ใช้ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)" ไม่มีข้อมูลผู้จองอื่น (booking-policy)
6. export ใน `__init__.py` แล้วรัน Proof ทั้งสองคำสั่ง

## Risks
- FR-1: สัปดาห์ที่ชนต้องข้ามและรายงาน ไม่ล้มทั้งชุด และไม่สร้างครึ่ง ๆ เมื่อ `weeks` ไม่ถูกต้อง
- FR-2: ครั้งที่เกิน 30 วันต้องเป็น `BEYOND_HORIZON` ไม่ใช่ `TOO_FAR_AHEAD` ที่ทำให้ทั้งชุดล้ม
- PDPA: ห้ามใส่ `user_id` ของผู้จองอื่นในข้อความหรือ repr ของ skipped
- test เดิม 17 ข้อต้องยังผ่าน (ห้ามแก้ test เดิม)

## Proof
- `python -m pytest` → ต้องเห็น `N passed` (N ≥ 22) และไม่มี failed
- `python ../cdg-acceptance/check.py RR` → `ACCEPTANCE 6/6`
