"""
Conversions for time slot end times.

A slot's `end_time` is stored as the end the user PICKED minus one second (picked 12:15 PM ->
12:14:59), so back-to-back slots never share an instant - see app/models/schema.py's TimeSlot.
Everything user-facing works with the PICKED end; these helpers convert at the DB boundary.
A picked end of 12:00 AM (00:00) means midnight, i.e. the end of the day, and is stored as 23:59:59.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

_BASE = date(2000, 1, 1)
_ONE_SECOND = timedelta(seconds=1)
MIDNIGHT = time(0, 0)


def stored_end_time(picked_hour: int, picked_minute: int) -> time:
    """The value to store for a picked end: 12:15 -> 12:14:59, and 00:00 (midnight) -> 23:59:59."""
    return (datetime.combine(_BASE, time(picked_hour, picked_minute)) - _ONE_SECOND).time()


def picked_end_time(stored: time) -> time:
    """The end the user picked / should see for a stored `end_time` (23:59:59 comes back as 00:00)."""
    return (datetime.combine(_BASE, stored) + _ONE_SECOND).time()


def start_minutes(hour: int, minute: int) -> int:
    return hour * 60 + minute


def end_minutes(picked_hour: int, picked_minute: int) -> int:
    """Minutes since midnight for a picked end, with 00:00 meaning the END of the day (1440),
    so 'end after start' can be compared numerically."""
    return 24 * 60 if (picked_hour, picked_minute) == (0, 0) else picked_hour * 60 + picked_minute


def snap_to_quarter_hour(minute: int) -> int:
    """Guards the minute dropdowns (00/15/30/45) against a value that was written outside this app."""
    return (minute // 15) * 15


def format_time_12h(t: time) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


def format_end_12h(stored: time) -> str:
    picked = picked_end_time(stored)
    return "12:00 AM (midnight)" if picked == MIDNIGHT else format_time_12h(picked)


def format_end_24h(stored: time) -> str:
    picked = picked_end_time(stored)
    return "24:00" if picked == MIDNIGHT else picked.strftime("%H:%M")
