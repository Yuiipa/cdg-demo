ทำตาม @intent/fr6-small-room-limit/spec.md แบบ TDD

ขั้นแรกเขียนเฉพาะ test ของ FR-6 ลงไฟล์ใหม่ tests/test_fr6_small_room.py (ห้ามแก้ test เดิม) แล้วรัน python -m pytest เป็นคำสั่งเดี่ยว รายงานบรรทัดสรุปของ pytest ตรงตัว จากนั้นจบเทิร์นทันที ยังไม่ต้องแก้โค้ดใน booking/ ในเทิร์นนี้

ถ้ามีข้อความจาก Stop hook ให้ทำตามข้อความนั้น (แก้โค้ดใน booking/ จน test ผ่าน แล้วรัน python -m pytest ใหม่ก่อนจบ)
