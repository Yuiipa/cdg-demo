# Review: <branch> เทียบกับ main
Branch: <feature/fr6-small-room> · Reviewer agent run by: <ชื่อ Driver> · วันที่: <วันที่> · Spec: intent/fr6-small-room-limit/spec.md

> กติกา: ตาราง Findings ต้องตรงกับที่ agent รายงาน ห้ามเพิ่มหรือตัด · คนเป็นผู้ตัดสิน (ช่อง triage และ Verdict ของคน) ไม่ใช่ agent · evidence ต้องชี้ file:line หรือผลคำสั่ง ไม่ใช่คำบอกเล่า

## Findings

| # | file:line | severity | issue | evidence | triage |
|---|---|---|---|---|---|
| 1 | <booking/service.py:42> | <blocker / should / nit> | <ปัญหา 1 บรรทัด> | <บรรทัดที่อ้าง / ชื่อ test / คำสั่ง → ผล> | <fix / wontfix / question> |

triage (Partner กรอก): `fix` = Driver แก้ในเทิร์นถัดไป · `wontfix` = ไม่แก้ บอกเหตุผลสั้น ๆ · `question` = ต้องถาม PO / QA ก่อน

## Verdict
- Agent: <approve / request-changes>
- Human: <approve / request-changes> โดย <ชื่อ Partner> (reviewer) · เหตุผล 1 บรรทัด: <…>

## Tests
- `python -m pytest` (agent รายงาน): <บรรทัด N passed ตรงตัว>
- `python -m pytest` (คนรันเองใน terminal 2): <บรรทัด N passed ตรงตัว>
- `git diff --stat main -- tests/test_rules.py tests/test_service.py`: <ว่าง / ไม่ว่าง>
