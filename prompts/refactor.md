# Template: สั่ง refactor (Role, Context, Task, Constraint, Format)

Role: senior <ภาษา> developer ที่รักษา behavior เดิม 100%
Context: เป้าหมาย <ไฟล์/ฟังก์ชัน> ปัญหา: <ซ้ำซ้อน/ยาว/ชื่อไม่สื่อ>
  มี test ที่ <ไฟล์ test> รันด้วย <คำสั่ง>
Task: refactor <สิ่งที่ต้องการ> โดยไม่เปลี่ยน public API
Constraint: รัน test ก่อนและหลัง ต้องผ่านเท่าเดิม
  ห้ามเปลี่ยน signature ที่ถูกเรียกจากไฟล์อื่น
  ห้ามแตะไฟล์นอก <ขอบเขต> ห้ามเพิ่ม dependency
  ถ้ามีอะไรไม่ชัด ให้ถามก่อนลงมือ
Format: เสนอรายการขั้นตอนก่อน (ขั้นละ 1 บรรทัด) รอยืนยัน
  แล้วทำทีละขั้น รายงาน diff และผล test ทุกขั้น

<!-- ถ้ายังไม่มี test: สั่งให้เขียน characterization test ล็อก behavior เดิมก่อน (ใช้ prompt_test.md) แล้วค่อย refactor -->
