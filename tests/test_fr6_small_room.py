"""Tests ของกฎ FR-6: จำกัดเวลาจองห้องเล็ก (ความจุไม่เกิน 6 ที่นั่ง)."""

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


def book(service, room_id, start, end):
    return service.create_booking(room_id, "somchai", start, end)


def test_fr6_small_room_two_hours_ok(service):
    # R1: 2 ชั่วโมงพอดีจองได้ (ขอบรวม)
    b = book(service, "R102", datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 12, 0))
    assert b.is_active


def test_fr6_small_room_too_long_rejected(service):
    # R2: เกิน 2 ชั่วโมงถูกปฏิเสธด้วย SMALL_ROOM_TOO_LONG และข้อความระบุรหัสห้อง+ขีดจำกัด
    with pytest.raises(BookingError) as exc:
        book(service, "R102", datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 12, 1))
    assert exc.value.code == "SMALL_ROOM_TOO_LONG"
    assert "R102" in exc.value.message
    assert "2 ชั่วโมง" in exc.value.message


def test_fr6_large_room_uses_fr3_limit(service):
    # R3: ห้องใหญ่กว่า 6 ที่นั่งใช้กฎ FR-3 เดิม (จอง 3 ชั่วโมงได้ ไม่ถูกจำกัดแบบห้องเล็ก)
    b = book(service, "R101", datetime(2026, 10, 6, 9, 0), datetime(2026, 10, 6, 12, 0))
    assert b.is_active


def test_fr6_checked_after_fr3_short_duration(service):
    # R4: ตรวจ FR-6 หลัง FR-3 ดังนั้นจองสั้นกว่า 30 นาทีได้ INVALID_DURATION เหมือนเดิม (ไม่ใช่ SMALL_ROOM_TOO_LONG)
    with pytest.raises(BookingError) as exc:
        book(service, "R102", datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 10, 15))
    assert exc.value.code == "INVALID_DURATION"


def test_fr6_recurring_small_room_first_occurrence_rejected(service):
    # R5: การจองซ้ำรายสัปดาห์ของห้องเล็กต้องผ่านกฎนี้ด้วย ครั้งแรกไม่ผ่าน -> ปฏิเสธทั้งคำขอ
    with pytest.raises(BookingError) as exc:
        service.create_recurring_booking(
            "R102",
            "somchai",
            datetime(2026, 10, 6, 10, 0),
            datetime(2026, 10, 6, 13, 0),
            weeks=2,
        )
    assert exc.value.code == "SMALL_ROOM_TOO_LONG"
    assert service.list_bookings("R102") == []
