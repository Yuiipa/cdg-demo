# Spec: การจองห้องประชุมซ้ำรายสัปดาห์ (Recurring weekly booking)
Status: approved     Source: BOOK-142
Intent: intent/recurring-booking/intent.md

## Requirements
R1. `BookingService.create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult` สร้างการจองครั้งแรกที่ `start`–`end` แล้วสร้างครั้งถัดไปห่างกันครั้งละ +7 วันที่เวลาเดิม รวม `weeks` ครั้ง (นับรวมครั้งแรก) ทุกการจองในชุดเดียวกันมี `Booking.series_id` เดียวกัน (ไม่ใช่ `None`) ส่วนการจองเดี่ยวเดิม (`create_booking`) ยังคง `series_id = None` (P5)

R2. ถ้า `weeks` ไม่ใช่จำนวนเต็ม หรือ < 1 ให้ reject ทั้งคำขอด้วย `BookingError("INVALID_RECURRENCE", …)` โดยไม่สร้างการจองแม้แต่ครั้งเดียว

R3. ถ้า `weeks` > 4 ให้ reject ทั้งคำขอด้วย `BookingError("RECURRENCE_TOO_LONG", …)` โดยไม่สร้างการจองแม้แต่ครั้งเดียว (P2: ค่าสูงสุดต่อชุดคือ 4 ครั้ง รวมครั้งแรก)

R4. ก่อนเริ่มสร้างชุด ตรวจครั้งแรกครั้งเดียว: ห้อง (`ROOM_NOT_FOUND`), ช่วงเวลา (`INVALID_TIME_RANGE`), ระยะเวลา (`INVALID_DURATION`), เวลาทำการ (`OUTSIDE_BUSINESS_HOURS`) และ FR-2 ของครั้งแรก (`IN_THE_PAST` / `TOO_FAR_AHEAD`) — ถ้าไม่ผ่านข้อใดข้อหนึ่ง ให้ reject ทั้งคำขอทันที ไม่สร้างแม้แต่ครั้งเดียว (P3: "ครั้งแรกใช้กฎ FR-2 เดิม ปฏิเสธทั้งคำขอ")

R5. จับเวลา `now = self._clock()` ครั้งเดียวตอนเริ่มเรียก (เวลาที่ส่งคำขอ) แล้วใช้ค่าเดียวกันตรวจ "ล่วงหน้าไม่เกิน 30 วัน" ของทุกสัปดาห์ในชุด ไม่คำนวณใหม่ระหว่างวนลูป (P3)

R6. แต่ละสัปดาห์ในชุด (รวมสัปดาห์แรก) หลังผ่าน R4 ให้ตรวจ "30 วันจาก `now`" ก่อนเสมอ (P3: "ตรวจ 30 วันก่อนตรวจการชน") ถ้าเกิน 30 วัน ให้ข้ามสัปดาห์นั้นด้วย `SkippedOccurrence(start, code="BEYOND_HORIZON", message="เกินระยะจองล่วงหน้า 30 วัน จองสัปดาห์นี้ภายหลังได้")` แล้วไปสัปดาห์ถัดไปต่อ ไม่ reject ทั้งชุด (P3, P7)

R7. สัปดาห์ที่ผ่าน R6 แล้ว ให้ตรวจ FR-1 (ห้ามจองซ้อน) กับข้อมูลจริง ณ ขณะนั้น (รวมสัปดาห์แรกด้วย) — ชนกันให้ข้ามสัปดาห์นั้นด้วย `SkippedOccurrence(start, code="BOOKING_OVERLAP", message="ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)")` แล้วไปสัปดาห์ถัดไปต่อ ไม่ reject ทั้งชุด (P1, P6) — ข้อความนี้ห้ามมีชื่อ เบอร์โทร อีเมล หรือ `user_id` ของผู้จองคนอื่นปรากฏอยู่เด็ดขาด

R8. สัปดาห์ที่ผ่านทั้ง R6 และ R7 ต้องบันทึกจริงด้วย `repo.save_booking` (เหมือน `create_booking`) และถูกเพิ่มเข้า `RecurringResult.created`

R9. การยกเลิกรายครั้งใช้ `cancel_booking(booking_id, cancelled_by)` เดิม ไม่เพิ่ม method ใหม่ และต้องไม่กระทบการจองครั้งอื่นในชุดเดียวกัน (กฎ FR-5 เดิมยังบังคับใช้ตามปกติต่อการจองแต่ละรายการ) (P4)

R10. ทุกการสร้าง การข้าม (skip) และการยกเลิก ต้องตรวจย้อนได้ว่าใคร (`user_id`) ทำอะไร (`booking_id`/`series_id` หรือห้อง+เวลาที่ขอ) ผลเป็นอย่างไร (`status`/`code`) โดยใช้ field ที่มีอยู่ในโมเดลเท่านั้น ไม่สร้างระบบ log ใหม่

R11. เพิ่ม `Booking.series_id: str | None = None` ใน `booking/models.py` และ export `RecurringResult`, `SkippedOccurrence` จาก `booking/__init__.py` โดยไม่เปลี่ยน public interface เดิมของ `create_booking`, `cancel_booking`, `list_bookings`

## Design
ไฟล์ที่แตะ: `booking/models.py` (เพิ่ม `series_id`, dataclass `RecurringResult` และ `SkippedOccurrence`), `booking/service.py` (เพิ่ม method `create_recurring_booking` ใน `BookingService`), `booking/__init__.py` (export เพิ่ม)

API contract (fixed ตาม `architect_note.md`, ห้ามเปลี่ยนชื่อ/ลำดับ/ชนิด):
```
BookingService.create_recurring_booking(room_id: str, user_id: str, start: datetime, end: datetime, weeks: int) -> RecurringResult
```

อัลกอริทึม (ตามการตัดสินของ PO ใน `intent/sources/recurring/po_decisions.md`):
1. ตรวจ `weeks` เป็นจำนวนเต็ม 1–4 (R2, R3) — reject ทั้งคำขอถ้าไม่ผ่าน
2. `now = self._clock()` (R5)
3. ตรวจห้อง/ช่วงเวลา/ระยะเวลา/เวลาทำการ/FR-2 ของครั้งแรกด้วย `now` (R4) — reject ทั้งคำขอถ้าไม่ผ่าน
4. สร้าง `series_id` ใหม่ 1 ค่าต่อการเรียก 1 ครั้ง
5. วนลูป i = 0..weeks-1: `occurrence_start = start + 7i วัน`, `occurrence_end = end + 7i วัน`
   - ถ้า `occurrence_start - now > 30 วัน` → skip `BEYOND_HORIZON` (R6) ไปสัปดาห์ถัดไป
   - ไม่งั้น ตรวจ overlap (FR-1) → ชน: skip `BOOKING_OVERLAP` (R7); ไม่ชน: บันทึกและเพิ่มใน `created` (R8)
6. คืนค่า `RecurringResult(created=created, skipped=skipped)`
7. ยกเลิก: ใช้ `cancel_booking` เดิมไม่มีการเปลี่ยนแปลง (R9)

## Constraint mapping
- booking-policy (PDPA / error code / audit, owner DPO) -> R1, R7 (ข้อความ `BOOKING_OVERLAP` ไม่เปิดเผยตัวตนผู้อื่น ตาม P6), R10
- security-baseline (validate input ที่ boundary, reject ด้วย BookingError ไม่ใช่ bare exception, log เฉพาะ id/code, owner Security) -> R2, R3, R4, R10
- ux-messages (บอกเหตุ+ทางไปต่อ เป็นภาษาไทยสุภาพ, owner UX lead) -> R6, R7 (ข้อความตาม P6/P7 ที่ PO ชี้ขาดแล้วว่า privacy ชนะในส่วนที่ขัดกัน)
- FR-1 ถึง FR-5 เดิม (docs/spec_meeting_room_booking.docx) -> R4, R6, R7, R9

## Open questions
ไม่มีประเด็นที่ยังเปิดค้างสำหรับขอบเขตนี้ — ทุกข้อที่เคยเปิดไว้ถูกตัดสินแล้วโดย PO ใน `intent/sources/recurring/po_decisions.md` (ดู Decision log) รายการต่อไปนี้ถูกประกาศว่า **นอกขอบเขตของรอบนี้อย่างชัดเจน** ไม่ใช่สิ่งที่ engineering ต้องตัดสินใจเอง: ยกเลิกทั้งชุดในคำสั่งเดียว, วันหยุดนักขัตฤกษ์, หน้าจอและการแจ้งเตือน, การจองซ้ำแบบรายวันหรือรายเดือน

## Areas of concern
- ข้อความปฏิเสธขัดกันระหว่างนโยบาย: `ux-messages` ข้อ 2 กำหนดให้บอกว่าใครถือสิทธิ์ช่วงเวลานั้นเพื่อให้ต่อรองได้ (เช่น ชื่อ/ติดต่อผู้จอง) แต่ `booking-policy` (PDPA) ห้ามแสดงชื่อ/เบอร์/อีเมล/`user_id` ของผู้อื่นโดยเด็ดขาด และ intent.md เองระบุว่าฝ่ายกฎหมายเคยเตือนเรื่องนี้มาก่อน **แก้ไขแล้ว:** PO ตัดสิน (ร่วมกับ DPO, UX lead รับทราบ) ว่า privacy ชนะ ใช้ข้อความ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)" แทน — ดู P6 ใน Decision log และ R7 · owner: DPO, UX lead
- จำนวนครั้งสูงสุดต่อชุดที่ยังไม่กำหนด มีผลทั้งด้าน UX (ข้อความตอน reject) และ security (ป้องกัน loop ยาวเกินจนกระทบ performance) **แก้ไขแล้ว:** PO กำหนดเป็น 4 ครั้งต่อชุด — ดู P2 ใน Decision log และ R3 · owner: PO, Security
- การจองล่วงหน้าทั้งไตรมาส (เป้าหมายหลักของ intent) อาจขัดกับ FR-2 (30 วัน) ถ้า PO ตัดสินให้ FR-2 บังคับใช้ทุกสัปดาห์ สัปดาห์ที่เกิน ~4 สัปดาห์แรกจะถูก skip หมด ทำให้ feature นี้ใช้ประโยชน์ตามเป้าหมายของ intent ไม่ได้จริง ควรแจ้ง trade-off นี้ให้ PO ทราบก่อนตัดสิน **แก้ไขแล้ว:** PO ยืนยันไม่แก้ FR-2 และรับทราบว่า "1 ไตรมาสในครั้งเดียว" ยังทำไม่ได้ในรอบนี้ (จำกัดที่ 4 ครั้ง/ชุดตาม P2 ด้วย) ถือเป็นข้อจำกัดที่ยอมรับแล้ว ไม่ใช่สิ่งที่ engineering ต้องแก้เพิ่ม — ดู P3 ใน Decision log และ R4, R6 · owner: PO
- Audit: โมเดลปัจจุบัน (`Booking`) ไม่มี timestamp ของ "เมื่อไรที่สร้าง/ยกเลิก" ถ้าต้องตรวจสอบย้อนหลังระดับ audit log ที่ละเอียดกว่านี้ (เช่น ใครเรียก API เมื่อไร) ต้องเพิ่มระบบ log ระดับ platform ซึ่งอยู่นอกขอบเขตของ `BookingService` ตามนโยบาย booking-policy ข้อ 3 · owner: platform team
- ยังไม่มี unit test คุ้มครอง `create_recurring_booking` (เป็น method ใหม่) ทีม engineering ต้องเขียน test ใหม่ตามข้อกำหนด NFR ใน spec .docx ("ทุกกฎต้องมี unit test ครอบคลุมทั้งกรณีผ่านและกรณีผิดพลาด") โดยห้ามแก้ `tests/test_rules.py`, `tests/test_service.py` ที่ถูก protect ไว้ · owner: engineering

## Decision log
- ใช้สัญญา API ตาม `architect_note.md` ตรงตัวทั้งชื่อ ลำดับ และชนิดพารามิเตอร์ ไม่เปลี่ยนแปลง · โดย สถาปนิกระบบ (fixed contract, BOOK-142) · 2026-10-14
- P1 ข้ามเฉพาะสัปดาห์ที่ชนกัน (ไม่ยกเลิกทั้งชุด) ใช้กับทุกสัปดาห์รวมสัปดาห์แรก · P2 `weeks` สูงสุด 4 ครั้งต่อชุด เกินไป reject ทั้งคำขอด้วย `RECURRENCE_TOO_LONG` · P3 ไม่แก้ FR-2 เดิม ตรวจ 30 วันจากเวลาที่ส่งคำขอก่อนตรวจการชน สัปดาห์เกินให้ `skipped` ด้วย `BEYOND_HORIZON` ครั้งแรกยังปฏิเสธทั้งคำขอด้วยกฎ FR-2 เดิม · P4 ยกเลิกทีละครั้งด้วยกลไกเดิม ยกเลิกทั้งชุดนอกขอบเขต · P5 ทุกครั้งในชุดมี `series_id` เดียวกัน · P6 privacy ชนะข้อขัดแย้งกับ ux-messages ข้อความคือ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)" ห้ามเปิดเผยตัวตนผู้จองอื่น · P7 ข้อความ `BEYOND_HORIZON` คือ "เกินระยะจองล่วงหน้า 30 วัน จองสัปดาห์นี้ภายหลังได้" · โดย Product Owner (ร่วมกับ DPO ในข้อ P6; UX lead รับทราบ) ตามเอกสาร `intent/sources/recurring/po_decisions.md` · 2026-10-14
