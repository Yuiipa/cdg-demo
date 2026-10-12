# Template: สั่งเขียน test

Role: QA engineer ที่คิด edge case เก่ง
Context: ฟังก์ชัน <ชื่อ> ใน <ไฟล์> ทำหน้าที่ <อธิบาย>
  framework: <pytest/jest>   สไตล์ test เดิมดูที่ <ไฟล์>
Task: เขียน test ครอบคลุม happy path, boundary, error case
  และ case ที่เคยพลาด: <ระบุ>
Constraint: ห้ามแก้โค้ดจริงเพื่อให้ test ผ่าน
  ถ้า test fail ให้รายงานว่าเป็น bug หรือ test ผิด
  ห้ามใช้ sleep หรือเรียก service จริง ใช้ fixture หรือ mock
Format: ตารางรายการ test (ชื่อ, สิ่งที่ตรวจ, ผล) ตามด้วยไฟล์ test และผลการรัน
