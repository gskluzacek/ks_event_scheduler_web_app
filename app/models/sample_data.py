"""
Seeded fake data, held in module-level lists.

Everything in this file resets when the app restarts. It exists purely so the
mock UI has something believable to render, filter, and edit. When we move
past mocking, these lists get replaced by SQLite queries - the page code
should ideally not need to change much beyond the data-access layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models.schema import (
    Account, Alliance, Event, Kingdom, Player, Role, TimeSlot, TimeZone,
    next_id,
)

time_zones: list[TimeZone] = [
    TimeZone("America/New_York", "UTC-05:00"),
    TimeZone("America/Chicago", "UTC-06:00"),
    TimeZone("America/Los_Angeles", "UTC-08:00"),
    TimeZone("Europe/London", "UTC+00:00"),
    TimeZone("Europe/Berlin", "UTC+01:00"),
    TimeZone("Asia/Tokyo", "UTC+09:00"),
    TimeZone("Australia/Sydney", "UTC+10:00"),
]

kingdoms: list[Kingdom] = [
    Kingdom(next_id(), "Kingdom 1042"),
    Kingdom(next_id(), "Kingdom 2077"),
]

alliances: list[Alliance] = [
    Alliance(next_id(), "Crimson Vanguard", kingdoms[0].id, "1101010101", "Crimson Vanguard HQ"),
    Alliance(next_id(), "Iron Covenant", kingdoms[0].id, "1101010102", "Iron Covenant Guild"),
    Alliance(next_id(), "Shattered Throne", kingdoms[1].id, "1101010103", "Shattered Throne"),
]

accounts: list[Account] = [
    Account(next_id(), "111111111111111111", "Greg#0001", None, "America/Chicago", is_super_admin=True),
    Account(next_id(), "222222222222222222", "Aria#4821", None, "America/New_York"),
    Account(next_id(), "333333333333333333", "Kestrel#0099", None, "Europe/London"),
    Account(next_id(), "444444444444444444", "Nox#7712", None, "Asia/Tokyo"),
]

players: list[Player] = [
    Player(next_id(), accounts[0].id, alliances[0].id, "KS-10042", "Greg", "GregTheBold", 84000, 28,
           roles=[Role.POWER_ADMIN]),
    Player(next_id(), accounts[1].id, alliances[0].id, "KS-20391", "Aria", "AriaStorm", 61250, 25,
           roles=[Role.ADMIN]),
    Player(next_id(), accounts[2].id, alliances[0].id, "KS-30512", "Kestrel", "KestrelV", 45300, 22,
           roles=[Role.SCHEDULER_ADMIN]),
    Player(next_id(), accounts[3].id, alliances[1].id, "KS-40118", "Nox", "NoxUnbound", 39900, 20,
           roles=[Role.USER]),
]

events: list[Event] = [
    Event(next_id(), alliances[0].id, "Kingdom vs Kingdom", "Cross-kingdom war window",
          scheduled_start=datetime.utcnow() + timedelta(days=2), is_published=True),
    Event(next_id(), alliances[0].id, "Bear Trap", "Weekly bear trap coordination"),
    Event(next_id(), alliances[1].id, "Castle Battle", "Alliance castle defense"),
]

time_slots: list[TimeSlot] = [
    TimeSlot(next_id(), players[0].id, events[0].id,
             datetime.utcnow() + timedelta(days=2, hours=1),
             datetime.utcnow() + timedelta(days=2, hours=3)),
    TimeSlot(next_id(), players[1].id, events[0].id,
             datetime.utcnow() + timedelta(days=2, hours=2),
             datetime.utcnow() + timedelta(days=2, hours=4), needs_review=True),
    TimeSlot(next_id(), players[2].id, events[1].id,
             datetime.utcnow() + timedelta(days=5, hours=0),
             datetime.utcnow() + timedelta(days=5, hours=1)),
]
