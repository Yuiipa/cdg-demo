---
name: security-baseline
description: "Security baseline for code changes in this repository (owner Security). Use when designing or changing code that handles input, errors, logging, configuration, secrets or dependencies. Thai keywords - ตรวจ input, ข้อมูลลับ, log, dependency ใหม่."
---

# Security baseline (owner: Security)

1. **Validate input** at the service boundary (required fields, types, ranges). Reject with a `BookingError` code, never with a bare exception or a stack trace.
2. **No secrets** in code, logs, messages or test fixtures. Read secrets from the environment; never open, print or copy `.env`.
3. **Log ids and codes only**, not personal data.
4. **No new third-party dependency without approval** from the tech lead and Security. Propose it as an area of concern instead of adding it.

Policy owner: Security. Changes to this skill need Security sign-off.
