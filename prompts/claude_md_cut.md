ปรับ CLAUDE.md ให้ตรงกับ @docs/templates/CLAUDE.template.md ไม่เกิน 60 บรรทัด มี 5 หัวข้อ Commands / Conventions / Architecture / Things Claude gets wrong / Verifying your work

- ใส่เฉพาะสิ่งที่ new joiner ต้องรู้ในวันแรกและหาเองจากโค้ดไม่ได้
- ใน Things Claude gets wrong ใส่
  (1) ห้ามแก้หรือลบ test เดิม ถ้า test เดิมขัดกับงานให้หยุดแล้วเขียน artifacts/escalation.md
  (2) การจองที่ชนขอบ (จบ 11:00/เริ่ม 11:00) ไม่ถือว่าซ้อน และการจองที่ยกเลิกแล้วไม่นับ
- ใน Commands ใส่ `python -m pytest` (ผลปกติ: "N passed") `python scripts/docx2md.py <file.docx>` และ `python scripts/pii_scan.py <file>`
- ส่วน Verifying your work ใช้ข้อความตาม template
- แก้เฉพาะ CLAUDE.md ไฟล์เดียว ไม่สร้างไฟล์อื่น ไม่ต้อง commit (ผม commit เอง)
