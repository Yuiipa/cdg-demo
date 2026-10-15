อ่าน mcp_server/internal_tools/server.py และ mcp_server/internal_tools/data.py แล้ววางแผนสร้างไฟล์ใหม่ mcp_server/internal_tools/day2_tools.py ที่ลงทะเบียน tool เพิ่ม 2 ตัวบน `mcp` ตัวเดิม (import ด้วย `from internal_tools.server import mcp` ตามที่ server.py เตรียม extension point ไว้)

1. list_incidents(status: str = "") อ่านอย่างเดียว คืน INCIDENTS จาก data.py (กรองตาม status ถ้าระบุ)
2. create_ticket(summary: str, description: str, reporter: str = "claude-code") สร้าง ticket ใหม่ key BOOK-<เลขถัดไปจาก key สูงสุดใน TICKETS> status "To Do" ใส่ลง TICKETS และ append 1 บรรทัด JSON ลง artifacts/tickets_created.jsonl (สร้างโฟลเดอร์ถ้ายังไม่มี) คืน {"ok": true, "key": ...}

กติกา: ห้ามแก้ server.py และ data.py · ห้าม print ไป stdout (stdout เป็นช่อง MCP) · docstring ของ tool เป็นภาษาไทย 1 บรรทัดและบอกว่าเป็น tool อ่านหรือเขียน · เขียน test ใน tests/test_day2_tools.py ที่เรียกฟังก์ชันตรง ๆ (ไม่ต้องเปิด server) · ห้ามแก้ test เดิม

ถามผมได้ไม่เกิน 2 คำถาม แล้วสรุปแผนสั้น ๆ รอผมอนุมัติก่อนเขียนไฟล์
