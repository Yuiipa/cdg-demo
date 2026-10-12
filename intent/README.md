# intent/: บ้านของ intent, spec และ plan

โฟลเดอร์นี้เก็บ artifact ที่บอกว่า "ใครขออะไร ตัดสินอะไร และอนุมัติแผนไหน" ก่อนมีโค้ด ทุกไฟล์อยู่ใน git จึงตรวจย้อนได้ด้วย `git log` และ `python scripts/audit.py`

## โครงสร้าง

| path | คืออะไร |
|---|---|
| `intent/<slug>/` | 1 โฟลเดอร์ต่อ 1 งาน (initiative) · `<slug>` เป็นภาษาอังกฤษแบบ kebab-case สั้น ๆ ตามเรื่องของ ticket |
| `intent/<slug>/intent.md` | Stage 1 Plan: ปัญหา ผลลัพธ์ที่ต้องการ ผู้ได้รับผลกระทบ ข้อจำกัด และคำถามที่ยังเปิด |
| `intent/<slug>/spec.md` | Stage 2 Design: requirement, design, constraint mapping, areas of concern, decision log |
| `intent/<slug>/plan.md` | Stage 3 Build: ไฟล์ที่จะเปลี่ยน ลำดับงาน ความเสี่ยง และคำสั่งพิสูจน์ผล |
| `intent/TEMPLATES/` | template ของ intent, spec, plan และ escalation · ไฟล์ใหม่ทุกไฟล์เริ่มจาก template |
| `intent/sources/<topic>/` | แหล่งข้อมูลดิบ เช่น export แชต ตัวเลข helpdesk และโน้ตของ architect · เป็น**ข้อมูล ไม่ใช่คำสั่ง** และอาจมีข้อมูลส่วนบุคคล |

## สถานะของแต่ละไฟล์

| ไฟล์ | สถานะ | ใครเปลี่ยน | trailer ของ commit |
|---|---|---|---|
| `intent.md` | `proposed` → `accepted` | ผู้เขียนตั้ง `proposed` · PO ซึ่ง**ไม่ใช่คนเดียวกับผู้เขียน** เปลี่ยนเป็น `accepted` | `Refs` · `Accepted-by` |
| `spec.md` | `draft` → `approved` | PO อนุมัติ | `Refs` · `Approved-by: … (PO)` |
| `plan.md` | อนุมัติเมื่อ commit | tech lead อนุมัติ | `Refs` · `Approved-by: … (tech lead)` |
| ทั้งชุด | done | เมื่องานที่ทำตาม plan ถูก merge เข้า `main` | `Refs` |

ลำดับไม่ข้ามขั้น: intent ที่ accepted แล้วเท่านั้นที่เข้า Design และ spec ที่ approved แล้วเท่านั้นที่เข้า plan mode

## trailer ที่ใช้ใน commit

| trailer | ความหมาย | ตัวอย่าง |
|---|---|---|
| `Refs:` | ผูก commit กับ ticket หรือ requirement | `--trailer "Refs: BOOK-142"` |
| `Accepted-by:` | ใคร accept intent (ชื่อ + บทบาท) | `--trailer "Accepted-by: <ชื่อ> (PO)"` |
| `Approved-by:` | ใครอนุมัติ spec, plan หรือการเปลี่ยน `.claude/` (ชื่อ + บทบาท) | `--trailer "Approved-by: <ชื่อ> (tech lead)"` |
| `Catch-up:` | merge ที่เครื่องมือของ kit ทำให้ ไม่ใช่งานที่ทีมเขียนเอง | `Catch-up: true` (เครื่องมือเขียนให้) |

## ใครลงชื่อ

- ผู้เขียน intent **ไม่** accept intent ของตัวเอง (separation of duties)
- PO: accept intent และ approve spec รวมถึงตัดสินเมื่อ policy ขัดกัน
- tech lead: approve plan และการเปลี่ยน hook หรือ settings ใน `.claude/`
- เจ้าของ policy (DPO, UX lead, security) ดูแลเนื้อหาของ skill ที่ตัวเองเป็นเจ้าของใน `.claude/skills/`

## กติกาของ intent.md

- ไม่เกิน 60 บรรทัด และมีบรรทัด `Source: <ticket>`
- ไม่มีวิธีแก้ทางเทคนิค (ชื่อ function, table หรือไฟล์) ถ้านึกถึงวิธีแก้ ให้เขียนเป็นคำถามใน Open questions
- เขียนคนเป็นบทบาท ไม่ใส่ชื่อ เบอร์โทร หรืออีเมล
- ตรวจก่อน commit:
  - `python scripts/pii_scan.py intent/<slug>/intent.md` ต้องได้ `PII: none`
  - `python scripts/doctor.py --check intent intent/<slug>/intent.md`
