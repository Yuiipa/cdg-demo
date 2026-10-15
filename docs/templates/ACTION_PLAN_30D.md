# 30-Day Action Plan: <ชื่อทีม / ระบบ>
ผู้เขียน: <ชื่อ> (<บทบาท>) · วันที่: <วันที่> · ส่งผู้สอนภายใน 17:00 ถ้ายังไม่เสร็จ (ไฟล์อยู่ใน my/ ไม่ต้อง commit)

> กติกา: ใช้เรื่องจริงของทีม แต่ห้ามใส่โค้ด ข้อมูลลูกค้า หรือข้อมูลลับของบริษัท · ก่อนส่งรัน `python scripts/pii_scan.py my/ACTION_PLAN_30D.md` ต้องได้ `PII: none`
> ถ้าเวลาไม่พอ (cut rule 15:30): กรอก §1 กับแถว "ตัวตรวจผล" และ "ผู้อนุมัติ" ใน §2 ในห้องก่อน ที่เหลือส่งภายใน 48 ชั่วโมง

## §1 เครื่องมือ agentic 1 ตัวที่จะทำจริง (จาก Loop Canvas)
- ชื่อ / งานที่ทำ (1 ประโยค): <…>
- trigger: <คนสั่ง / PR เปิด / เวลา / event>
- รูปแบบ: <subagent / claude -p ใน CI / /schedule / MCP tool>
- ใครได้ประโยชน์ก่อน: <บทบาท>

## §2 Loop governance
| ข้อ | คำตอบของทีม |
|---|---|
| ตัวตรวจผล (oracle) และใครเป็นคนรัน | <…> |
| stop rule (ผ่าน / รอบสูงสุด / งบ) | <…> |
| เจ้าของ escalation (ใคร ช่องทางไหน) | <…> |
| protected paths (อะไรที่ agent ห้ามแตะ) | <…> |
| ผู้อนุมัติก่อนมีผลจริง (ลงชื่อที่ไหน) | <…> |
| log / หลักฐานอยู่ไหน | <…> |

## §3 MCP access
- tool อ่าน (allow): <…>
- tool เขียน (ask): <…>
- deny: <…>
- ใครเป็นเจ้าของ server และใคร review tool ใหม่ก่อนเปิดใช้: <บทบาท>

## §4 สัปดาห์ W1–W4
| สัปดาห์ | ทำอะไร | ผลที่ตรวจได้ | เจ้าของ |
|---|---|---|---|
| W1 | CLAUDE.md + protect/stop hooks บน repo เดียว: <repo ไหน> | <เช่น hooks.py test all ผ่าน · commit ที่เปิด hook มี Approved-by> | <…> |
| W2 | reviewer agent บน PR: <repo / ทีมไหน> | <เช่น REVIEW.md ใน PR ทุกอัน · คน triage ทุก finding> | <…> |
| W3 | MCP server สำหรับระบบภายใน 1 ระบบ: <ระบบไหน> | <เช่น tool อ่าน allow · tool เขียน ask · มี log> | <…> |
| W4 | headless ใน CI + ข้อเสนอ managed settings: <…> | <เช่น claude -p รันใน CI ด้วย --allowedTools · ข้อเสนอส่ง security แล้ว> | <…> |

## §5 เจ้าของและตัวชี้วัด
- เจ้าของแผน: <ชื่อ / บทบาท>
- leading indicator (วัดได้จาก git หรือ CI ทันที): <เช่น % commit ที่มี Refs: · จำนวนครั้งที่ hook บล็อกต่อสัปดาห์>
- lagging indicator (เห็นผลใน 30 วัน): <เช่น เวลา review เฉลี่ยต่อ PR · bug ที่หลุดไป production>
- ผล pii_scan: <วางบรรทัดสุดท้าย>
