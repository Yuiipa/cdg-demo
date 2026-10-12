---
name: booking-policy
description: "Booking privacy (PDPA), audit and error-message policy for the meeting-room booking service (owner DPO). Use when writing, reviewing or designing user-facing error or rejection messages, BookingError codes and Thai messages, what to record when a booking is created, cancelled or rejected (audit, cancellation records), logs, or anything that shows who booked a room or another person's details. Thai keywords - ข้อความ error, ข้อความแจ้งผู้ใช้, จองไม่ได้, ยกเลิก, บันทึก, audit, PDPA, ข้อมูลส่วนบุคคล."
---

# Booking policy (owner: DPO)

Apply these rules whenever a change creates, cancels or rejects a booking, or shows a message to a user. Full text and examples: [policy.md](policy.md).

1. **PDPA: store and show the minimum.** A booking stores `user_id` only. A message, log line or exception text must never show another person's name, email, phone number or `user_id`. Users may see their own booking details.
2. **Errors.** Reject with `BookingError(code, message)`. `code` is the UPPER_SNAKE_CASE code from the spec (never invent one when the spec already has one). `message` is polite Thai, says what the user can do next, and contains no personal data of anyone else.
3. **Audit trail.** Every create, cancel and reject must be traceable afterwards: who acted (`user_id`), what (`booking_id`, or the requested room and time), the result (`status` or the error `code`), and when. Cancelling never deletes a booking: it sets `status = "CANCELLED"`.
4. **Conflicts.** If another policy or a UX request asks to reveal another person's details, do not decide yourself: record it as an area of concern with owner DPO plus the other policy's owner, and let the PO decide.

Policy owner: DPO. Changes to this skill need DPO sign-off.
