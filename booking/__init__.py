"""Meeting room booking: โปรเจกต์ตัวอย่างสำหรับคอร์ส Claude Code (CDG)."""

from booking.models import Booking, Room
from booking.service import BookingError, BookingService
from booking.storage import InMemoryRepository

__all__ = ["Booking", "Room", "BookingError", "BookingService", "InMemoryRepository"]
