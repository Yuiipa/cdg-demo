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

    @property
    def is_active(self) -> bool:
        return self.status == "CONFIRMED"
