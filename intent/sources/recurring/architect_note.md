# Architect note: recurring booking (BOOK-142)
Author: สถาปนิกระบบ (ทีม platform) · Status: fixed contract
Source: BOOK-142

สัญญา API ที่ตกลงกับทีม booking แล้ว งาน BOOK-142 ต้องใช้ชื่อ พารามิเตอร์ และชนิดข้อมูลตามนี้ตรงตัว
QA เขียน acceptance จากสัญญานี้ ชื่ออื่นหรือลำดับพารามิเตอร์อื่นจะไม่ผ่าน

## Contract

```
BookingService.create_recurring_booking(room_id, user_id, start, end, weeks) -> RecurringResult
```

| พารามิเตอร์ | ชนิด | ความหมาย |
|---|---|---|
| room_id | str | ห้อง เช่น R101 |
| user_id | str | ผู้จอง (เก็บแค่ id ตาม PDPA) |
| start | datetime | เวลาเริ่มของครั้งแรก |
| end | datetime | เวลาสิ้นสุดของครั้งแรก |
| weeks | int | จำนวนครั้งทั้งหมด นับรวมครั้งแรก ครั้งถัดไปคือ +7 วัน เวลาเดิม |

## Types (booking/models.py)
- `RecurringResult` (dataclass): `created: list[Booking]`, `skipped: list[SkippedOccurrence]`
- `SkippedOccurrence` (dataclass): `start: datetime`, `code: str`, `message: str`
  - `code` = รหัสของ BookingError ที่ทำให้สัปดาห์นั้นจองไม่ได้ หรือรหัสรายสัปดาห์ที่ PO กำหนด
  - `message` = ข้อความภาษาไทยที่แสดงต่อผู้ใช้
- `Booking.series_id: str | None = None` ทุกครั้งในชุดเดียวกันมีค่าเดียวกัน การจองเดี่ยวเป็น `None`
- export `RecurringResult` และ `SkippedOccurrence` จาก `booking/__init__.py`

## Errors
- ปฏิเสธทั้งคำขอด้วย `BookingError("RECURRENCE_TOO_LONG", …)` เมื่อ `weeks` เกินจำนวนสูงสุดต่อชุด (ตัวเลขยังเปิดอยู่: PO เป็นคนกำหนด)
- `weeks` น้อยกว่า 1 หรือไม่ใช่จำนวนเต็ม: `BookingError("INVALID_RECURRENCE", …)`
- ห้อง ช่วงเวลา ระยะเวลา หรือเวลาทำการของช่วงที่ขอไม่ถูกต้อง: ใช้รหัสเดิมของระบบ (`ROOM_NOT_FOUND`, `INVALID_TIME_RANGE`, `INVALID_DURATION`, `OUTSIDE_BUSINESS_HOURS`)
- ยกเลิกรายครั้ง: ใช้ `cancel_booking(booking_id, cancelled_by)` เดิม ไม่เพิ่ม method ใหม่

## ไม่ได้ตัดสินในเอกสารนี้ (ถาม PO)
- จำนวนครั้งสูงสุดต่อชุด
- สัปดาห์ที่จองไม่ได้ (ห้องไม่ว่าง หรือเหตุอื่นตามกฎเดิม) จะจัดการอย่างไร และผู้ใช้เห็นข้อความอะไร
- การยกเลิกทั้งชุด
