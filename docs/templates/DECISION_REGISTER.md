# Decision Register: <ชื่อทีม / ระบบ>
ผู้กรอก: <ชื่อ> (<บทบาท>) · อัปเดตล่าสุด: <วันที่>

กติกา: ทุกแถวต้องมี **เจ้าของ** (บทบาทหรือชื่อ) และ **วันที่ต้องตัดสิน** แม้ยังไม่รู้คำตอบ
การตัดสินใจที่ไม่มีเจ้าของ คือการตัดสินใจที่ Claude จะทำแทนคุณ
ค่าแนะนำคือสิ่งที่ห้องเรียนทำ ไม่ใช่คำตอบของทีมคุณ ให้แก้ให้ตรงกับทีม
Status: open → proposed → decided (ใส่ลิงก์หรือ commit ที่บันทึกการตัดสินใจ)

## วันที่ 1 (D1–D7)

| # | Decision | ตัวเลือก | ค่าแนะนำ (จากห้องเรียน) | เจ้าของ | วันที่ | Status |
|---|---|---|---|---|---|---|
| D1 | ที่เก็บ intent + source of truth + รูปแบบ ID | repo / ระบบ legacy (Jira, ServiceNow) / linkage | `intent/<เรื่อง>/` ใน repo · ticket อ่านผ่าน MCP · trailer `Refs: <ticket>` |  |  | open |
| D2 | ใคร accept intent.md / ใคร approve spec.md | PO / BA / tech lead | PO accept (คนที่สองลงชื่อจริง) · PO approve spec.md |  |  | open |
| D3 | เจ้าของ policy ของแต่ละ skill + ช่องทาง sign-off | DPO / UX lead / security | 1 skill = 1 owner · policy ขัดกัน → PO ตัดสินกับ owner |  |  | open |
| D4 | งานแบบไหนต้องมี plan.md + ใครอนุมัติ | ทุกงาน / ตาม risk tier | เกณฑ์ที่สังเกตได้ (เช่น แตะ > 2 module, spec มาจาก ticket) · งานเสี่ยงสูง → tech lead |  |  | open |
| D5 | เจ้าของ CLAUDE.md + กระบวนการ "mistake twice" | tech lead / ทั้งทีมผ่าน PR | code owner อนุมัติใน PR · Claude พลาดซ้ำ 2 ครั้ง → แก้ CLAUDE.md |  |  | open |
| D6 | permission mode เริ่มต้น + เมื่อไรใช้ auto | auto / manual / accept edits / plan | ระบุโหมดทุกครั้ง · auto เฉพาะงาน routine ที่มี test ครอบ |  |  | open |
| D7 | hook ไหนอยู่ใน git ทีม / ไหนอยู่ใน managed settings | `.claude/settings.json` / managed | hook ของทีมอยู่ใน git · hook ที่ห้ามปิดอยู่ใน managed (แผน Team/Enterprise) |  |  | open |

## วันที่ 2 (D8–D14) กรอกในช่วง Action Plan วันที่ 2

| # | Decision | ตัวเลือก | ค่าแนะนำ | เจ้าของ | วันที่ | Status |
|---|---|---|---|---|---|---|
| D8 | protected paths ของ oracle + ใครแก้ test ได้ | QA / ทีม dev / ทุกคน | (กรอกวันที่ 2) |  |  | open |
| D9 | เจ้าของ eval suite + gate ของการเปลี่ยน config | QA / platform / tech lead | (กรอกวันที่ 2) |  |  | open |
| D10 | REVIEW.md: เกณฑ์ที่ต้องให้คนตรวจ + path ที่ต้องให้คน review เสมอ | tech lead / security | (กรอกวันที่ 2) |  |  | open |
| D11 | autonomy tier ต่อ environment + ผู้อนุมัติ production gate + เงื่อนไข CHG | dev / staging / prod | (กรอกวันที่ 2) |  |  | open |
| D12 | control band แรก: metric, baseline, tier responses, ผู้ triage | service owner / SRE | (กรอกวันที่ 2) |  |  | open |
| D13 | เส้นทางโมเดล + ชั้นความลับต่อ repo | public / internal / confidential / restricted | (กรอกวันที่ 2) |  |  | open |
| D14 | marketplace ที่อนุมัติ + นโยบาย third-party skill + managed settings ที่จะขอ | security / platform | (กรอกวันที่ 2) |  |  | open |
