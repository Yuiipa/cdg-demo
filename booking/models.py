"""Domain models ของระบบจองห้องประชุม."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class Room:
    """ห้องประชุม 1 ห้อง."""

    room_id: str
    name: str
    capacity: int


@dataclass
class Booking:
    """รายการจองห้องประชุม 1 รายการ (เก็บแค่ user_id ของผู้จอง)."""

    room_id: str
    user_id: str
    start: datetime
    end: datetime
    title: str = ""
    booking_id: str = field(default_factory=lambda: uuid4().hex[:8])
    status: str = "CONFIRMED"  # CONFIRMED | CANCELLED
    series_id: str | None = None  # ค่าเดียวกันทุกครั้งในชุดการจองรายสัปดาห์ (BOOK-142)

    @property
    def is_active(self) -> bool:
        return self.status == "CONFIRMED"


@dataclass
class SkippedOccurrence:
    """ครั้งในชุดที่จองไม่ได้: ไม่มีข้อมูลของผู้จองคนอื่น (booking-policy / PDPA)."""

    start: datetime
    code: str
    message: str


@dataclass
class RecurringResult:
    """ผลการจองรายสัปดาห์: ครั้งที่จองได้ และครั้งที่ข้าม."""

    created: list[Booking] = field(default_factory=list)
    skipped: list[SkippedOccurrence] = field(default_factory=list)
