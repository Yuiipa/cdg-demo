อ่าน @intent/recurring-booking/spec.md (approved) และ CLAUDE.md แล้วสัมภาษณ์ผมก่อนวางแผน ถามทีละข้อ ไม่เกิน 4 ข้อ

จากนั้นเสนอแผนตามหัวข้อใน @intent/TEMPLATES/plan.template.md (Files that change / Order of work / Risks / Proof) โดย

- **ข้อ 0 ของ Order of work ต้องเป็น: "บันทึกแผนนี้เป็น intent/recurring-booking/plan.md ตาม template แล้วหยุดรอคำสั่ง ห้ามแก้ไฟล์อื่น"**
- Files that change: path จริงทุกไฟล์ ทั้งไฟล์ใหม่และไฟล์ที่แก้
- Risks: อะไรพังได้ รวมถึงผลต่อกฎการจองเดิม (FR-1 ถึง FR-5) · ต้องมีบรรทัดขึ้นต้นด้วย `FR-1:` (สัปดาห์ที่ห้องชน) และ `FR-2:` (สัปดาห์ที่เกิน 30 วัน) ตาม po_decisions.md
- Proof ต้องมี `python -m pytest` และ `python ../cdg-acceptance/check.py RR`
- ใช้ชื่อ function ตาม @intent/sources/recurring/architect_note.md
- แผนไม่เกิน 40 บรรทัด
- `../cdg-acceptance` เป็นของผู้เรียน: ห้ามอ่าน ตรวจ หรือรันอะไรในนั้น และห้ามใส่ขั้นตอนเกี่ยวกับ check.py ใน Order of work หรือ Risks (เขียนไว้แค่ใน Proof)
