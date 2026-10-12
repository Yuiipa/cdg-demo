"""BOOK-142: จองซ้ำรายสัปดาห์ ตาม intent/recurring-booking/spec.md (R1-R7)."""

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


def tue(day: int, hour: int) -> datetime:
    return datetime(2026, 10, day, hour, 0)


def test_series_shares_series_id(service):  # R1
    result = service.create_recurring_booking("R102", "team-lead", tue(6, 14), tue(6, 15), 4)
    assert len(result.created) == 4
    assert result.skipped == []
    ids = {b.series_id for b in result.created}
    assert len(ids) == 1 and None not in ids
    assert [b.start.day for b in result.created] == [6, 13, 20, 27]


def test_too_many_weeks_rejected_and_nothing_created(service):  # R2
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R102", "team-lead", tue(6, 14), tue(6, 15), 6)
    assert exc.value.code == "RECURRENCE_TOO_LONG"
    assert service.list_bookings("R102") == []


def test_invalid_first_slot_raises_existing_code(service):  # R3
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R102", "team-lead", tue(6, 17), tue(6, 19), 2)
    assert exc.value.code == "OUTSIDE_BUSINESS_HOURS"
    assert service.list_bookings("R102") == []


def test_conflicting_and_far_weeks_are_skipped(service):  # R4 + R5
    service.create_booking("R102", "someone-else", tue(27, 14), tue(27, 15))
    result = service.create_recurring_booking("R102", "team-lead", tue(20, 14), tue(20, 15), 4)
    assert [b.start for b in result.created] == [tue(20, 14), datetime(2026, 11, 3, 14, 0)]
    assert [(s.start, s.code) for s in result.skipped] == [
        (tue(27, 14), "BOOKING_OVERLAP"),
        (datetime(2026, 11, 10, 14, 0), "BEYOND_HORIZON"),
    ]


def test_cancel_single_occurrence(service):  # R6
    result = service.create_recurring_booking("R102", "team-lead", tue(6, 14), tue(6, 15), 3)
    service.cancel_booking(result.created[1].booking_id, "team-lead")
    active = service.list_bookings("R102")
    assert [b.start.day for b in active] == [6, 20]
    assert result.created[1].status == "CANCELLED"


def test_skipped_message_hides_other_booker(service):  # R7
    service.create_booking("R102", "wichai.p@example.com", tue(13, 14), tue(13, 15))
    result = service.create_recurring_booking("R102", "team-lead", tue(6, 14), tue(6, 15), 2)
    (skipped,) = result.skipped
    assert skipped.message == "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)"
    assert "wichai" not in repr(skipped) and "@" not in repr(skipped)
