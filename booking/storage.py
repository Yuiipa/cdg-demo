"""ที่เก็บข้อมูลแบบ in-memory (แทน database จริงสำหรับ demo)."""

from __future__ import annotations

from booking.models import Booking, Room


class InMemoryRepository:
    """เก็บห้องและรายการจองไว้ในหน่วยความจำ."""

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._bookings: dict[str, Booking] = {}

    # ---- rooms -------------------------------------------------------
    def add_room(self, room: Room) -> None:
        self._rooms[room.room_id] = room

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def list_rooms(self) -> list[Room]:
        return list(self._rooms.values())

    # ---- bookings ----------------------------------------------------
    def save_booking(self, booking: Booking) -> None:
        self._bookings[booking.booking_id] = booking

    def get_booking(self, booking_id: str) -> Booking | None:
        return self._bookings.get(booking_id)

    def list_bookings(self, room_id: str | None = None) -> list[Booking]:
        items = list(self._bookings.values())
        if room_id is not None:
            items = [b for b in items if b.room_id == room_id]
        return sorted(items, key=lambda b: b.start)
