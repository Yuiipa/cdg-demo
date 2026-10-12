# Spec: จองห้องประชุมซ้ำรายสัปดาห์

Status: approved     Source: BOOK-142
Intent: intent/recurring-booking/intent.md

## Requirements
- R1 ผู้ใช้สร้างชุดการจองรายสัปดาห์ได้ในคำขอเดียว: ห้องเดิม วันในสัปดาห์เดิม เวลาเดิม จำนวน `weeks` ครั้ง ทุกครั้งในชุดใช้ `series_id` เดียวกัน
- R2 จองได้สูงสุด 4 ครั้งต่อชุด ถ้า `weeks` เกิน 4 ให้ปฏิเสธทั้งคำขอด้วย `RECURRENCE_TOO_LONG` และไม่สร้างอะไรเลย (`weeks` น้อยกว่า 1 → `INVALID_RECURRENCE`)
- R3 ช่วงเวลาที่ขอ (ครั้งแรก) ต้องผ่านกฎเดิม: ห้องมีจริง เวลาถูกต้อง FR-2 FR-3 FR-4 ถ้าไม่ผ่านให้ raise code เดิมและไม่สร้างอะไรเลย
- R4 ทุกครั้งในชุดต้องผ่าน FR-1..FR-4 ครั้งที่ห้องไม่ว่าง (FR-1) ให้ข้ามและรายงานใน `skipped` ด้วย code `BOOKING_OVERLAP` ครั้งอื่นยังจองต่อ
- R5 ทุกครั้งต้องอยู่ภายใน 30 วันของ FR-2 ครั้งที่เกินให้ข้ามและรายงานด้วย code `BEYOND_HORIZON`
- R6 ยกเลิกได้ทีละครั้งด้วย `cancel_booking(booking_id, cancelled_by)` เดิม ครั้งอื่นในชุดยัง active
- R7 ข้อความใน `skipped` เป็นภาษาไทย และห้ามระบุตัวผู้จองคนอื่น: ใช้ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)" (booking-policy)

## Design
- API (ตาม architect_note.md): `create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult` ใน `BookingService`
- `booking/models.py`: `RecurringResult(created: list[Booking], skipped: list[SkippedOccurrence])` และ `SkippedOccurrence(start, code, message)`
- `Booking.series_id: str | None = None` ค่าเดียวกันทุกครั้งในชุด · export `RecurringResult`, `SkippedOccurrence` จาก `booking/__init__.py`
- ตรวจ `weeks` ก่อน → ตรวจครั้งแรก (R3) → วนทีละสัปดาห์ (`start + 7 วัน × i`) ใช้ rule เดิมของ service ไม่เขียนกฎซ้ำ
- `TOO_FAR_AHEAD` ของครั้งที่ 2 เป็นต้นไปแปลงเป็น `BEYOND_HORIZON` ใน `skipped`

## Constraint mapping
- booking-policy (PDPA): เก็บแค่ `user_id` · ข้อความ skipped ไม่มีชื่อ อีเมล เบอร์ของผู้อื่น (R7) · error ผ่าน `BookingError(code, message)` ภาษาไทย
- ux-messages: ผู้ใช้ต้องรู้ว่าสัปดาห์ไหนจองไม่ได้และควรทำอะไรต่อ → รายงานทุกครั้งที่ข้ามพร้อมวันที่และทางติดต่อ (R4, R5, R7)
- security-baseline: ตรวจ input (`weeks` เป็นจำนวนเต็ม 1..4, ห้องมีจริง) · ไม่ log ข้อมูลส่วนบุคคล · ไม่เพิ่ม dependency

## Open questions
- รายงานการใช้ห้อง (BOOK-143) ควรนับชุดการจองเป็น 1 รายการหรือหลายรายการ (ไม่อยู่ในขอบเขตนี้)

## Areas of concern
- A1 ผู้ใช้อยากได้ "1 ไตรมาส" แต่ FR-2 จองล่วงหน้าได้ไม่เกิน 30 วัน · owner: PO
- A2 ข้อความเมื่อจองไม่ได้: ux-messages ให้บอกว่าใครจองไว้ แต่ booking-policy ห้ามเปิดเผยผู้จองอื่น · owner: DPO + UX lead

## Decision log
- A1: สูงสุด 4 ครั้ง ทุกครั้งอยู่ใน 30 วัน ครั้งที่เกินถูกข้ามด้วย `BEYOND_HORIZON` (PO, ตาม po_decisions.md)
- A2: privacy ชนะ UX แจ้งแค่ "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)" ไม่ระบุผู้จองอื่น (PO + DPO)
- สัปดาห์ที่ชนให้ข้ามและรายงาน ไม่ยกเลิกทั้งชุด · ยกเลิกได้ทีละครั้ง (PO)
