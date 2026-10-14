# Plan: Recurring weekly booking (from intent/recurring-booking/spec.md)

## Files that change
- `booking/models.py` — เพิ่ม `Booking.series_id: str | None = None` (ท้าย dataclass), `RecurringResult(created, skipped)`, `SkippedOccurrence(start, code, message)`
- `booking/service.py` — เพิ่ม method `BookingService.create_recurring_booking`
- `booking/__init__.py` — export `RecurringResult`, `SkippedOccurrence`
- `tests/test_recurring_booking.py` — ไฟล์ใหม่ (ไม่ถูก protect)

## Order of work
0. บันทึกแผนนี้เป็น intent/recurring-booking/plan.md ตาม template แล้วหยุดรอคำสั่ง ห้ามแก้ไฟล์อื่น
1. models.py: เพิ่ม `series_id`, `RecurringResult`, `SkippedOccurrence`
2. `booking/__init__.py`: export 2 type ใหม่
3. service.py: `create_recurring_booking(room_id, user_id, start, end, weeks)` — validate `weeks` เป็น int 1–4 ไม่ผ่าน reject ทั้งคำขอ (`INVALID_RECURRENCE`/`RECURRENCE_TOO_LONG`)
4. `now = self._clock()` ครั้งเดียว เก็บไว้ใช้ตลอดลูป ห้ามเรียกซ้ำ
5. ตรวจครั้งแรกด้วยของเดิม (room/time/`_check_duration`/`_check_business_hours`/`_check_advance_window`) ไม่ผ่าน reject ทั้งคำขอ — **ไม่รวม overlap** overlap ของทุกสัปดาห์รวมสัปดาห์แรกเช็คในลูป (ข้อ 7-8) เท่านั้น
6. `series_id = uuid4().hex[:8]`; วน i=0..weeks-1 คำนวณ occurrence start/end = start/end + 7i วัน
7. ถ้า `occurrence_start - now > 30 วัน` (inline ใช้ `now` เดิม ไม่เรียก `_check_advance_window` ซ้ำ) → skip `BEYOND_HORIZON` ด้วยข้อความคงที่ "เกินระยะจองล่วงหน้า 30 วัน จองสัปดาห์นี้ภายหลังได้"
8. ไม่งั้น try ครอบเฉพาะ `self._check_overlap(room_id, occurrence_start, occurrence_end)` (except `BookingError`) → skip `BOOKING_OVERLAP` ด้วยข้อความคงที่ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)"; ผ่าน → สร้าง `Booking(...)` เอง (**ห้ามเรียก `self.create_booking()`**) + `repo.save_booking` + เก็บเข้า `created`
9. `tests/test_recurring_booking.py`: ครอบคลุมสำเร็จ/`INVALID_RECURRENCE`/`RECURRENCE_TOO_LONG`/reject ครั้งแรกผิด/skip `BEYOND_HORIZON`/skip `BOOKING_OVERLAP` (ไม่มี PII)/cancel รายครั้งไม่กระทบครั้งอื่น
10. รัน `python -m pytest` ให้ผ่านทั้งหมด รวม test เดิม

## Risks
- FR-1: สัปดาห์ที่ห้องชนกันต้อง skip เฉพาะสัปดาห์นั้น (รวมสัปดาห์แรก) ไม่ reject ทั้งชุด — พังถ้า except ดักผิด code หรือปล่อย `BookingError` หลุดจาก loop
- FR-2: สัปดาห์เกิน 30 วันจาก `now` ที่จับครั้งเดียวต้อง skip ไม่ reject ทั้งชุด — **ขั้นเสี่ยงที่สุด**: ถ้าเรียก `_check_advance_window` ซ้ำในลูปจะ `clock()` ใหม่ทุกครั้ง ขัด R5
- ห้ามเรียก `self.create_booking()` ในลูป — มันตรวจซ้ำครบทุกกฎและ raise ตรงๆ เมื่อชน ทำให้ reject ทั้งชุดแทนที่จะ skip เฉพาะสัปดาห์ (ขัด R7/P1); ต้องสร้าง `Booking(...)` + `repo.save_booking` เอง
- try ต้องครอบเฉพาะบรรทัดเรียก `_check_overlap()` ไม่ครอบ `save_booking` ด้วย ไม่งั้นจะกลืน error อื่นเงียบๆ
- ทางเลือกที่ไม่เลือก: เขียน validate/overlap logic ใหม่แยกจากของเดิม — ไม่เลือกเพราะซ้ำโค้ดและเสี่ยงกฎเพี้ยน (reuse ตามที่ยืนยันแล้ว)

## Proof
python -m pytest
python ../cdg-acceptance/check.py RR
