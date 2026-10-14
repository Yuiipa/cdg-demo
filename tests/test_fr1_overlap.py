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


def test_overlap_partial_rejected(service: BookingService) -> None:
    service.create_booking(
        room_id="R101",
        user_id="somchai",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
    )
    with pytest.raises(BookingError) as exc:
        service.create_booking(
            room_id="R101",
            user_id="malee",
            start=datetime(2026, 10, 6, 10, 30),
            end=datetime(2026, 10, 6, 11, 30),
        )
    assert exc.value.code == "BOOKING_OVERLAP"


def test_back_to_back_booking_succeeds(service: BookingService) -> None:
    service.create_booking(
        room_id="R101",
        user_id="somchai",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
    )
    booking = service.create_booking(
        room_id="R101",
        user_id="malee",
        start=datetime(2026, 10, 6, 11, 0),
        end=datetime(2026, 10, 6, 12, 0),
    )
    assert booking.is_active


def test_cancelled_booking_does_not_block_overlap(service: BookingService) -> None:
    existing = service.create_booking(
        room_id="R101",
        user_id="somchai",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
    )
    service.cancel_booking(existing.booking_id, cancelled_by="somchai")

    booking = service.create_booking(
        room_id="R101",
        user_id="malee",
        start=datetime(2026, 10, 6, 10, 30),
        end=datetime(2026, 10, 6, 11, 30),
    )
    assert booking.is_active


def test_same_time_different_room_succeeds(service: BookingService) -> None:
    service.create_booking(
        room_id="R101",
        user_id="somchai",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
    )
    booking = service.create_booking(
        room_id="R102",
        user_id="malee",
        start=datetime(2026, 10, 6, 10, 0),
        end=datetime(2026, 10, 6, 11, 0),
    )
    assert booking.is_active
