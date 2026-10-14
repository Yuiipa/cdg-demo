"""การจองห้องประชุมซ้ำรายสัปดาห์ (BOOK-142) ตาม intent/recurring-booking/spec.md."""

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


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute)


def test_create_recurring_booking_success(service: BookingService) -> None:
    result = service.create_recurring_booking(
        "R101", "u1", at(6, 10), at(6, 11), weeks=3
    )
    assert result.skipped == []
    assert [b.start for b in result.created] == [at(6, 10), at(13, 10), at(20, 10)]
    assert [b.end for b in result.created] == [at(6, 11), at(13, 11), at(20, 11)]
    series_ids = {b.series_id for b in result.created}
    assert len(series_ids) == 1
    assert None not in series_ids
    assert all(b.is_active for b in result.created)
    assert service.list_bookings("R101") == result.created


def test_create_recurring_booking_invalid_weeks_rejects_whole_request(
    service: BookingService,
) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R101", "u1", at(6, 10), at(6, 11), weeks=0)
    assert exc.value.code == "INVALID_RECURRENCE"
    assert service.list_bookings("R101") == []


def test_create_recurring_booking_non_int_weeks_rejects_whole_request(
    service: BookingService,
) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R101", "u1", at(6, 10), at(6, 11), weeks="3")
    assert exc.value.code == "INVALID_RECURRENCE"
    assert service.list_bookings("R101") == []


def test_create_recurring_booking_too_many_weeks_rejects_whole_request(
    service: BookingService,
) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R101", "u1", at(6, 10), at(6, 11), weeks=5)
    assert exc.value.code == "RECURRENCE_TOO_LONG"
    assert service.list_bookings("R101") == []


def test_create_recurring_booking_first_occurrence_invalid_rejects_whole_request(
    service: BookingService,
) -> None:
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking("R999", "u1", at(6, 10), at(6, 11), weeks=3)
    assert exc.value.code == "ROOM_NOT_FOUND"
    assert service.list_bookings("R101") == []


def test_create_recurring_booking_skips_week_beyond_30_day_horizon(
    service: BookingService,
) -> None:
    start = datetime(2026, 11, 2, 10, 0)  # +28 วัน 1 ชม. จาก NOW ยังอยู่ในระยะ 30 วัน
    end = datetime(2026, 11, 2, 11, 0)
    result = service.create_recurring_booking("R101", "u1", start, end, weeks=2)

    assert [b.start for b in result.created] == [start]
    assert len(result.skipped) == 1
    assert result.skipped[0].start == datetime(2026, 11, 9, 10, 0)  # +35 วัน เกินระยะ
    assert result.skipped[0].code == "BEYOND_HORIZON"
    assert result.skipped[0].message == "เกินระยะจองล่วงหน้า 30 วัน จองสัปดาห์นี้ภายหลังได้"


def test_create_recurring_booking_skips_overlapping_week_without_pii(
    service: BookingService,
) -> None:
    # สัปดาห์ที่ 2 (13 ต.ค.) ถูกคนอื่นจองไว้ก่อนแล้ว
    service.create_booking("R101", "other-user", at(13, 10), at(13, 11))

    result = service.create_recurring_booking(
        "R101", "u1", at(6, 10), at(6, 11), weeks=2
    )

    assert [b.start for b in result.created] == [at(6, 10)]
    assert len(result.skipped) == 1
    skipped = result.skipped[0]
    assert skipped.start == at(13, 10)
    assert skipped.code == "BOOKING_OVERLAP"
    assert skipped.message == "ห้องถูกจองแล้ว (ติดต่อฝ่ายอาคาร)"
    assert "other-user" not in skipped.message


def test_cancel_one_occurrence_does_not_affect_rest_of_series(
    service: BookingService,
) -> None:
    result = service.create_recurring_booking(
        "R101", "u1", at(6, 10), at(6, 11), weeks=2
    )
    first, second = result.created

    cancelled = service.cancel_booking(first.booking_id, cancelled_by="u1")

    assert cancelled.status == "CANCELLED"
    assert second.is_active
    remaining = service.list_bookings("R101")
    assert remaining == [second]
