# CLAUDE.md  (≤ 1 หน้า)

## Commands
- Test: python -m pytest   (ผลปกติ: "N passed")
- Read spec: python scripts/docx2md.py <file.docx>
- PII: python scripts/pii_scan.py <file>

## Conventions
- แก้ไฟล์ด้วย Edit/Write ห้าม shell redirect (>, >>, tee)
- <กฎของทีมที่อ่านจากโค้ดไม่ได้>

## Architecture
- <1–3 บรรทัด ชี้จุดที่หายาก ไม่ต้องไล่ทุกไฟล์>

## Things Claude gets wrong
- <เรื่องที่ Claude พลาดซ้ำ: เริ่มจาก 2 ข้อของเมื่อเช้า>

## Verifying your work
- Test: python -m pytest (all green: ต้องเห็น "N passed"; never skip or delete a failing test)
- Run the tests before reporting any task complete, and paste the output.
- If a test fails, fix the code, not the test.
- If a requirement conflicts with an existing test, don't change the test: write artifacts/escalation.md and stop.
