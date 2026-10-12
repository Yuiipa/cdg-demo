**Role:** senior Python developer ของทีม booking ยึด CLAUDE.md

**Context:** FR-1 ใน docs/spec_meeting_room_booking.docx (อ่านด้วย python scripts/docx2md.py) ข้อตกลง product: จองชนขอบได้ (end == start ไม่ถือว่าซ้อน) การจองที่ยกเลิกแล้วไม่นับ

**Task:** เพิ่มกฎ FR-1 ห้ามจองห้องเดียวกันซ้อนช่วงเวลา ใน create_booking (booking/service.py) โดย raise BookingError("BOOKING_OVERLAP", …)

**Constraint:** แก้เฉพาะ booking/service.py และสร้าง tests/test_fr1_overlap.py ห้ามแก้ test เดิม ห้ามเพิ่ม dependency ถ้าไม่ชัดให้ถามก่อน

**Format:** เสนอแผน 3–5 บรรทัดแล้วรอผมตอบ ok จบด้วยผล pytest ดิบและตาราง diff (ไฟล์ | บรรทัด | เหตุผล)
