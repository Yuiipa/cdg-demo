Implement ตาม @intent/recurring-booking/plan.md ทีละขั้นตาม Order of work (ข้ามข้อ 0 เพราะทำแล้ว)

- ทุกขั้นทำตาม "Verifying your work" ใน CLAUDE.md และแปะผล pytest ดิบ
- รัน `python -m pytest` เป็นคำสั่งเดี่ยว (ไม่ต่อ pipe, `;`, `&&` หรือ `cd … &&`) แล้วยกบรรทัด `N passed` มาตรงตัว ถ้าไม่มีบรรทัดนี้ ถือว่ายังไม่ผ่าน
- ถ้าต้องทำต่างจากแผน ให้แก้ plan.md ไปพร้อมกันและเขียนเหตุผล
- ห้ามแก้ test เดิม (tests/test_rules.py, tests/test_service.py, tests/test_fr1_overlap.py)
- ข้อความแจ้งผู้ใช้ต้องผ่าน booking-policy (PDPA)
- อย่าอ่านหรือรันอะไรใน ../cdg-acceptance (acceptance เป็นของ QA/PO ผมรันเอง)
- ยังไม่ต้อง commit (ผม commit ใน Part B หลังเปิด hook)
- จบด้วยตาราง: ขั้น | ไฟล์ที่แก้ | ผล pytest (บรรทัด N passed)
