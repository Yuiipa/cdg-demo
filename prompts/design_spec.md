**Role:** tech lead + analyst ของทีม booking

**Context:** intent.md ที่แนบมา (accepted แล้ว) · codebase ใน repo นี้ · `intent/sources/recurring/architect_note.md` (สัญญา API ที่ตกลงแล้ว) · `docs/spec_meeting_room_booking.docx` อ่านด้วย `python scripts/docx2md.py docs/spec_meeting_room_booking.docx` (รันเป็นคำสั่งเดี่ยว ไม่ต่อ pipe)

**Task:** "Read the attached intent.md and produce a requirements and design spec for integrating it into our existing codebase."

**Constraint:** "Apply the skills available to you so the plan conforms to our booking policy, UX standards and security baseline."
- ห้ามแก้โค้ดหรือ test เขียนแค่ไฟล์ spec.md ไฟล์เดียว ไม่ต้อง commit
- Design ใช้ signature ตาม architect_note.md ตรงตัว: `create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult`
- ตรวจ requirement ทุกข้อกับกฎ FR-1 ถึง FR-5 ใน spec .docx
- อะไรที่ intent, architect_note หรือ spec .docx ไม่ได้ตัดสิน ห้ามตัดสินเอง ให้เขียนเป็น Open questions หรือ Areas of concern

**Format:** "Document the spec fully as intent/recurring-booking/spec.md, ready to hand to the engineering team. Describe clearly any areas of concern, especially where you cannot satisfy contradicting policies."
- ใช้หัวข้อตาม `intent/TEMPLATES/spec.template.md` ครบทุกหัวข้อ · `Status: draft` · `Source: BOOK-142` · `Intent: intent/recurring-booking/intent.md`
- Requirements: R1, R2, … อย่างน้อย 5 ข้อ บรรทัดละ 1 ข้อที่ตรวจได้
- Constraint mapping: ชื่อ skill/policy ที่ใช้ → R ที่ตอบ policy นั้น
- Areas of concern: ทุกข้อมี `owner: <บทบาท>`
- ภาษาไทย ไม่เกิน 2 หน้า
