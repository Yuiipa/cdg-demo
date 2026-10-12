# cdg-claude-code-demo: ระบบจองห้องประชุม

โปรเจกต์ตัวอย่างสำหรับคอร์ส Claude Code ของ CDG เป็นบริการจองห้องประชุมแบบเก็บข้อมูลในหน่วยความจำ (in-memory) เขียนด้วย Python และทดสอบด้วย pytest ไม่มี dependency ตอนรันจริง

## เริ่มต้น (Git Bash)

terminal ของ VS Code ในโฟลเดอร์นี้เปิดเป็น Git Bash ให้เอง (ตั้งไว้ใน `.vscode/settings.json`) รันทีละบรรทัด:

```bash
python -m venv .venv
```

```bash
source .venv/Scripts/activate
```

```bash
python -m pip install -r requirements-dev.txt
```

```bash
python -m pytest
```

ผลที่ถูกต้อง: บรรทัดสุดท้ายเป็น `N passed in …` และไม่มี failed

ทุก terminal ใหม่ต้อง `source .venv/Scripts/activate` ก่อน (ต้องเห็น `(.venv)` หน้า prompt) · ถ้าจำเป็นต้องใช้ PowerShell ให้รัน test ด้วย `.venv\Scripts\python.exe -m pytest` เพราะคำสั่ง `source` ใช้ใน PowerShell ไม่ได้

## โครงสร้าง

| โฟลเดอร์ | มีอะไร |
|---|---|
| `booking/` | `models.py` (Room, Booking) · `storage.py` (InMemoryRepository) · `service.py` (BookingService และ BookingError) |
| `tests/` | pytest ของพฤติกรรมที่มีอยู่ตอนนี้ |
| `docs/` | `spec_meeting_room_booking.docx` เอกสาร requirement จากฝ่ายธุรกิจ (ไฟล์ Word) |

## ข้อตกลง

- ใช้ Python 3.11 ขึ้นไป
- รัน test ด้วย `python -m pytest` จาก root ของ repo
- ไฟล์ข้อความเป็น UTF-8 และขึ้นบรรทัดแบบ LF (ตั้งไว้ใน `.gitattributes`) · warning `LF will be replaced by CRLF` ไม่กระทบการทำงาน
