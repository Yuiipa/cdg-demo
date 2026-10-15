# Spec: จำกัดเวลาจองห้องเล็ก (FR-6)
Status: approved     Source: BOOK-188
Intent: intent/fr6-small-room-limit/intent.md

## Requirements
- R1 ห้องที่มีความจุไม่เกิน 6 ที่นั่ง ("ห้องเล็ก") จองได้ครั้งละไม่เกิน 2 ชั่วโมง (2 ชั่วโมงพอดีจองได้)
- R2 เกิน 2 ชั่วโมงให้ปฏิเสธด้วย `BookingError` code `SMALL_ROOM_TOO_LONG` ข้อความภาษาไทยระบุรหัสห้องและขีดจำกัด เช่น "ห้อง R102 เป็นห้องเล็ก จองได้ครั้งละไม่เกิน 2 ชั่วโมง"
- R3 ห้องที่ใหญ่กว่า 6 ที่นั่งใช้กฎ FR-3 เดิม (30 นาที ถึง 4 ชั่วโมง) test เดิมทุกตัวต้องผ่านโดยไม่แก้
- R4 ตรวจ FR-6 หลัง FR-3: การจองสั้นกว่า 30 นาทีได้ `INVALID_DURATION` เหมือนเดิม
- R5 การจองซ้ำรายสัปดาห์ของห้องเล็กต้องผ่านกฎนี้ด้วย (ครั้งแรกไม่ผ่าน → ปฏิเสธทั้งคำขอ)
- R6 ข้อความไม่มีข้อมูลส่วนบุคคล (booking-policy)

## Design
- `booking/service.py`: ค่าคงที่ `SMALL_ROOM_CAPACITY = 6` และ `SMALL_ROOM_MAX_DURATION = timedelta(hours=2)` · ตรวจใน `_check_duration` (มี `room` อยู่แล้ว) ต่อจากกฎ FR-3
- test ใหม่ใน `tests/test_fr6_small_room.py` ใช้ห้อง R101 (20 ที่นั่ง) และ R102 (6 ที่นั่ง) แบบเดียวกับ test เดิม ห้ามแตะ `tests/test_rules.py` และ `tests/test_service.py`

## Constraint mapping
- booking-policy → R6 · ux-messages → R2 (บอกห้องและขีดจำกัด) · security-baseline → ไม่เพิ่ม dependency

## Open questions
- ห้องขนาดกลาง (7–12 ที่นั่ง) ยังไม่ตัดสิน นอกขอบเขตนี้ ใช้ FR-3 ไปก่อน

## Areas of concern
- ไม่มี (PO ตัดสินแล้ว)

## Decision log
- ขอบ 2 ชั่วโมงนับรวม (PO, 2026-10-14)
- ใช้รหัสใหม่ `SMALL_ROOM_TOO_LONG` ไม่ใช้ `INVALID_DURATION` เพื่อให้หน้าจอแยกข้อความได้ (PO + UX lead)
- ห้ามแก้ test เดิม ถ้าขัดกันให้ escalate (QA lead)
