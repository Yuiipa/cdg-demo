from datetime import datetime

import pytest

from booking import BookingError, BookingService, InMemoryRepository, Room


@pytest.fixture
def repo() -> InMemoryRepository:
    repo = InMemoryRepository()
    repo.add_room(Room(room_id="R101", name="ห้องประชุมใหญ่", capacity=20))
    repo.add_room(Room(room_id="R102", name="ห้องประชุมเล็ก", capacity=6))
    return repo


@pytest.fixture
def service(repo: InMemoryRepository) -> BookingService:
    # ตรึงเวลาปัจจุบันไว้ที่ วันจันทร์ 5 ต.ค. 2026 09:00 เพื่อให้ผลทดสอบคงที่
    fixed_now = datetime(2026, 10, 5, 9, 0)
    return BookingService(repo, clock=lambda: fixed_now)


def test_create_booking_success(service: BookingService) -> None:
    booking = service.create_booking(
        room_id="R101",
        user_id="somchai",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
        title="ประชุมทีม",
    )
    assert booking.room_id == "R101"
    assert booking.is_active
    assert service.list_bookings("R101") == [booking]


def test_create_booking_unknown_room(service: BookingService) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_booking(
            room_id="R999",
            user_id="somchai",
            start=datetime(2026, 10, 6, 10, 0),
            end=datetime(2026, 10, 6, 11, 0),
        )
    assert exc.value.code == "ROOM_NOT_FOUND"


def test_create_booking_end_before_start(service: BookingService) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_booking(
            room_id="R101",
            user_id="somchai",
            start=datetime(2026, 10, 6, 11, 0),
            end=datetime(2026, 10, 6, 10, 0),
        )
    assert exc.value.code == "INVALID_TIME_RANGE"


def test_cancel_booking(service: BookingService) -> None:
    booking = service.create_booking(
        room_id="R102",
        user_id="somchai",
        start=datetime(2026, 10, 6, 13, 0),
        end=datetime(2026, 10, 6, 14, 0),
    )
    cancelled = service.cancel_booking(booking.booking_id, cancelled_by="somchai")
    assert cancelled.status == "CANCELLED"
    assert service.list_bookings("R102") == []
