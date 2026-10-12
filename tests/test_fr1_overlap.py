"""FR-1: ห้ามจองห้องเดียวกันซ้อนช่วงเวลา (ชนขอบได้ · การจองที่ยกเลิกแล้วไม่นับ)."""

from datetime import datetime

import pytest

from booking import BookingError, BookingService, InMemoryRepository, Room

NOW = datetime(2026, 10, 5, 9, 0)  # วันจันทร์


@pytest.fixture
def service() -> BookingService:
    repo = InMemoryRepository()
    repo.add_room(Room(room_id="R101", name="ห้องประชุมใหญ่", capacity=20))
    repo.add_room(Room(room_id="R102", name="ห้องประชุมเล็ก", capacity=6))
    return BookingService(repo, clock=lambda: NOW)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 6, hour, minute)


def test_fr1_partial_overlap_rejected(service):
    service.create_booking("R101", "u1", at(10), at(11))
    with pytest.raises(BookingError) as exc:
        service.create_booking("R101", "u2", at(10, 30), at(11, 30))
    assert exc.value.code == "BOOKING_OVERLAP"


def test_fr1_containment_rejected(service):
    service.create_booking("R101", "u1", at(10), at(12))
    with pytest.raises(BookingError) as exc:
        service.create_booking("R101", "u2", at(10, 30), at(11))
    assert exc.value.code == "BOOKING_OVERLAP"


def test_fr1_touching_allowed(service):
    service.create_booking("R101", "u1", at(10), at(11))
    assert service.create_booking("R101", "u2", at(11), at(12)).is_active
    assert service.create_booking("R102", "u3", at(10), at(11)).is_active  # คนละห้อง


def test_fr1_cancelled_booking_ignored(service):
    first = service.create_booking("R101", "u1", at(13), at(14))
    service.cancel_booking(first.booking_id, "u1")
    assert service.create_booking("R101", "u2", at(13), at(14)).is_active
