"""Tests ของกฎ FR-2 ถึง FR-5 (ตามตาราง Acceptance Scenarios ใน spec)."""

from datetime import datetime

import pytest

from booking import BookingError, BookingService, InMemoryRepository, Room

# เวลาปัจจุบันที่ตรึงไว้: วันจันทร์ 5 ต.ค. 2026 09:00
NOW = datetime(2026, 10, 5, 9, 0)


@pytest.fixture
def service() -> BookingService:
    repo = InMemoryRepository()
    repo.add_room(Room(room_id="R101", name="ห้องประชุมใหญ่", capacity=20))
    repo.add_room(Room(room_id="R102", name="ห้องประชุมเล็ก", capacity=6))
    return BookingService(repo, clock=lambda: NOW)


def book(service, start, end):
    return service.create_booking("R101", "somchai", start, end)


def test_fr2_too_far_ahead(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 11, 19, 10, 0), datetime(2026, 11, 19, 11, 0))  # 45 วัน
    assert exc.value.code == "TOO_FAR_AHEAD"


def test_fr2_in_the_past(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 10, 2, 10, 0), datetime(2026, 10, 2, 11, 0))
    assert exc.value.code == "IN_THE_PAST"


def test_fr3_duration_too_short(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 10, 15))
    assert exc.value.code == "INVALID_DURATION"


def test_fr3_duration_too_long(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 10, 6, 9, 0), datetime(2026, 10, 6, 13, 30))
    assert exc.value.code == "INVALID_DURATION"


def test_fr3_boundaries_inclusive(service):
    assert book(service, datetime(2026, 10, 6, 9, 0), datetime(2026, 10, 6, 9, 30)).is_active
    assert book(service, datetime(2026, 10, 7, 9, 0), datetime(2026, 10, 7, 13, 0)).is_active


def test_fr4_weekend_rejected(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 10, 10, 10, 0), datetime(2026, 10, 10, 11, 0))  # วันเสาร์
    assert exc.value.code == "OUTSIDE_BUSINESS_HOURS"


def test_fr4_after_hours_rejected(service):
    with pytest.raises(BookingError) as exc:
        book(service, datetime(2026, 10, 7, 17, 30), datetime(2026, 10, 7, 18, 30))
    assert exc.value.code == "OUTSIDE_BUSINESS_HOURS"


def test_fr5_cancel_too_late(service):
    b = book(service, datetime(2026, 10, 5, 9, 30), datetime(2026, 10, 5, 10, 30))  # เริ่มในอีก 30 นาที
    with pytest.raises(BookingError) as exc:
        service.cancel_booking(b.booking_id, "somchai")
    assert exc.value.code == "CANCEL_TOO_LATE"


def test_fr5_cancel_twice_rejected(service):
    b = book(service, datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 11, 0))
    service.cancel_booking(b.booking_id, "somchai")
    with pytest.raises(BookingError) as exc:
        service.cancel_booking(b.booking_id, "somchai")
    assert exc.value.code == "ALREADY_CANCELLED"
