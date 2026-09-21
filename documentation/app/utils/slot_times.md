# app/utils/slot_times.py

## Purpose
Conversions for time slot end times. The stored `end_time` is the end the user **picked** minus one second (picked 12:15 PM is
stored as `12:14:59`, and a midnight end as `23:59:59`), so back-to-back slots never share an instant. Everything user-facing
uses the picked end; these helpers convert at the boundary.

## Contents
- `stored_end_time(hour, minute)` / `picked_end_time(stored)` - the two directions (picked 12 AM / 00 means midnight).
- `start_minutes()` / `end_minutes()` - minutes since midnight for comparing "end after start" (a picked 00:00 end counts as 1440).
- `snap_to_quarter_hour(minute)` - guards the 00/15/30/45 dropdowns against a value written outside the app.
- `format_time_12h()`, `format_end_12h()` (midnight shows as `12:00 AM (midnight)`), `format_end_24h()` (midnight shows as `24:00`).
