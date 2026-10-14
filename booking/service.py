"""Business logic ของการจองห้องประชุม.

กฎทางธุรกิจตาม docs/spec_meeting_room_booking.docx
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from uuid import uuid4

from booking.models import Booking, RecurringResult, Room, SkippedOccurrence
from booking.storage import InMemoryRepository

MAX_ADVANCE = timedelta(days=30)
MIN_DURATION = timedelta(minutes=30)
MAX_DURATION = timedelta(hours=4)
BUSINESS_START = time(8, 0)
BUSINESS_END = time(18, 0)
MIN_CANCEL_NOTICE = timedelta(hours=1)
MAX_RECURRENCE_WEEKS = 4


class BookingError(Exception):
    """ข้อผิดพลาดทางธุรกิจ พร้อมรหัสข้อผิดพลาด (error code) สำหรับ API/UI."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BookingService:
    """จัดการการจองห้องประชุม."""

    def __init__(self, repo: InMemoryRepository, clock=None) -> None:
        self._repo = repo
        # clock() คืนค่า datetime ปัจจุบัน (ฉีดเข้ามาเพื่อให้ทดสอบได้)
        self._clock = clock or datetime.now

    def create_booking(
        self,
        room_id: str,
        user_id: str,
        start: datetime,
        end: datetime,
        title: str = "",
    ) -> Booking:
        room = self._repo.get_room(room_id)
        if room is None:
            raise BookingError("ROOM_NOT_FOUND", f"ไม่พบห้อง {room_id}")
        if end <= start:
            raise BookingError("INVALID_TIME_RANGE", "เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่ม")

        self._check_advance_window(start)  # FR-2
        self._check_duration(room, start, end)  # FR-3
        self._check_business_hours(start, end)  # FR-4
        self._check_overlap(room_id, start, end)  # FR-1

        booking = Booking(room_id=room_id, user_id=user_id, start=start, end=end, title=title)
        self._repo.save_booking(booking)
        return booking

    def create_recurring_booking(
        self,
        room_id: str,
        user_id: str,
        start: datetime,
        end: datetime,
        weeks: int,
    ) -> RecurringResult:
        if not isinstance(weeks, int) or weeks < 1:
            raise BookingError(
                "INVALID_RECURRENCE", "จำนวนสัปดาห์ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป"
            )
        if weeks > MAX_RECURRENCE_WEEKS:
            raise BookingError("RECURRENCE_TOO_LONG", "จองซ้ำได้ไม่เกิน 4 สัปดาห์ต่อชุด")

        now = self._clock()  # จับครั้งเดียว ใช้ตรวจ 30 วันของทุกสัปดาห์ในชุด (R5)

        room = self._repo.get_room(room_id)
        if room is None:
            raise BookingError("ROOM_NOT_FOUND", f"ไม่พบห้อง {room_id}")
        if end <= start:
            raise BookingError("INVALID_TIME_RANGE", "เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่ม")
        self._check_duration(room, start, end)  # FR-3
        self._check_business_hours(start, end)  # FR-4
        self._check_advance_window(start)  # FR-2 ของครั้งแรก (R4)

        series_id = uuid4().hex[:8]
        created: list[Booking] = []
        skipped: list[SkippedOccurrence] = []

        for i in range(weeks):
            occurrence_start = start + timedelta(days=7 * i)
            occurrence_end = end + timedelta(days=7 * i)

            if occurrence_start - now > MAX_ADVANCE:  # R6, ใช้ now เดิม ไม่เรียก _check_advance_window ซ้ำ
                skipped.append(
                    SkippedOccurrence(
                        start=occurrence_start,
                        code="BEYOND_HORIZON",
                        message="เกินระยะจองล่วงหน้า 30 วัน จองสัปดาห์นี้ภายหลังได้",
                    )
                )
                continue

            try:
                self._check_overlap(room_id, occurrence_start, occurrence_end)  # FR-1 (R7)
            except BookingError:
                skipped.append(
                    SkippedOccurrence(
                        start=occurrence_start,
                        code="BOOKING_OVERLAP",
                        message="ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)",
                    )
                )
                continue

            booking = Booking(
                room_id=room_id,
                user_id=user_id,
                start=occurrence_start,
                end=occurrence_end,
                series_id=series_id,
            )
            self._repo.save_booking(booking)  # R8
            created.append(booking)

        return RecurringResult(created=created, skipped=skipped)

    def cancel_booking(self, booking_id: str, cancelled_by: str) -> Booking:
        booking = self._repo.get_booking(booking_id)
        if booking is None:
            raise BookingError("BOOKING_NOT_FOUND", f"ไม่พบรายการจอง {booking_id}")
        if not booking.is_active:
            raise BookingError("ALREADY_CANCELLED", "รายการจองนี้ถูกยกเลิกไปแล้ว")
        if booking.start - self._clock() < MIN_CANCEL_NOTICE:  # FR-5
            raise BookingError("CANCEL_TOO_LATE", "ต้องยกเลิกล่วงหน้าอย่างน้อย 1 ชั่วโมงก่อนเวลาเริ่ม")
        booking.status = "CANCELLED"
        self._repo.save_booking(booking)
        return booking

    def list_bookings(self, room_id: str | None = None) -> list[Booking]:
        return [b for b in self._repo.list_bookings(room_id) if b.is_active]

    # ---- rules -------------------------------------------------------
    def _check_advance_window(self, start: datetime) -> None:
        now = self._clock()
        if start < now:
            raise BookingError("IN_THE_PAST", "ไม่สามารถจองเวลาที่ผ่านมาแล้วได้")
        if start - now > MAX_ADVANCE:
            raise BookingError("TOO_FAR_AHEAD", "จองล่วงหน้าได้ไม่เกิน 30 วัน")

    @staticmethod
    def _check_duration(room: Room, start: datetime, end: datetime) -> None:
        duration = end - start
        if duration < MIN_DURATION or duration > MAX_DURATION:
            raise BookingError(
                "INVALID_DURATION",
                f"ห้อง {room.room_id}: ระยะเวลาการจองต้องอยู่ระหว่าง 30 นาที ถึง 4 ชั่วโมง",
            )

    @staticmethod
    def _check_business_hours(start: datetime, end: datetime) -> None:
        if start.date() != end.date():
            raise BookingError("OUTSIDE_BUSINESS_HOURS", "การจองต้องอยู่ภายในวันเดียวกัน")
        if start.weekday() >= 5:
            raise BookingError("OUTSIDE_BUSINESS_HOURS", "จองได้เฉพาะวันจันทร์ถึงวันศุกร์")
        if start.time() < BUSINESS_START or end.time() > BUSINESS_END:
            raise BookingError("OUTSIDE_BUSINESS_HOURS", "จองได้เฉพาะเวลา 08:00 ถึง 18:00 น.")

    def _check_overlap(self, room_id: str, start: datetime, end: datetime) -> None:
        # ชนขอบได้ (end == start ไม่ถือว่าซ้อน) และการจองที่ยกเลิกแล้วไม่นับ
        for other in self._repo.list_bookings(room_id):
            if other.is_active and start < other.end and end > other.start:
                raise BookingError("BOOKING_OVERLAP", "ห้องนี้มีการจองในช่วงเวลาดังกล่าวแล้ว")
