"""
Seeded fake data, held in module-level lists.

Everything in this file resets when the app restarts. It exists purely so the
mock UI has something believable to render, filter, and edit. When we move
past mocking, these lists get replaced by SQLite queries - the page code
should ideally not need to change much beyond the data-access layer.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.models.schema import (
    Account, AccountType, Alliance, Event, Kingdom, Player, Role, TimeSlot,
    TimeSlotType, TimeZone, next_id,
)

time_zones: list[TimeZone] = [
    TimeZone(next_id(), "America", "New_York"),
    TimeZone(next_id(), "America", "Chicago"),
    TimeZone(next_id(), "America", "Los_Angeles"),
    TimeZone(next_id(), "Europe", "London"),
    TimeZone(next_id(), "Europe", "Berlin"),
    TimeZone(next_id(), "Asia", "Tokyo"),
    TimeZone(next_id(), "Australia", "Sydney"),
]

kingdoms: list[Kingdom] = [
    Kingdom(next_id(), "Kingdom 1042"),
    Kingdom(next_id(), "Kingdom 2077"),
]

alliances: list[Alliance] = [
    Alliance(next_id(), "Crimson Vanguard", kingdoms[0].id, "1517613215138189444", "Crimson Vanguard HQ"),
    # Real guild - Greg's corn-bot-1 is already a member, so this alliance can exercise the
    # actual bot-token guild-membership check end to end (see auth/discord_guild.py).
    Alliance(next_id(), "Iron Covenant", kingdoms[0].id,
             "1517613215138189444", "I am Jack's raging bile duct - test"),
    Alliance(next_id(), "Shattered Throne", kingdoms[1].id, "1517613215138189444", "Shattered Throne"),
]

accounts: list[Account] = [
    Account(next_id(), AccountType.DISCORD_USER, "Greg#0001", "America/Chicago",
            discord_user_id="835177531904098380", discord_username="Greg#0001",
            discord_global_name="Greg", is_super_admin=True),
    Account(next_id(), AccountType.DISCORD_USER, "Aria#4821", "America/New_York",
            discord_user_id="222222222222222222", discord_username="Aria#4821",
            discord_global_name="Aria"),
    Account(next_id(), AccountType.DISCORD_USER, "Kestrel#0099", "Europe/London",
            discord_user_id="333333333333333333", discord_username="Kestrel#0099",
            discord_global_name="Kestrel"),
    Account(next_id(), AccountType.DISCORD_USER, "Nox#7712", "Asia/Tokyo",
            discord_user_id="444444444444444444", discord_username="Nox#7712",
            discord_global_name="Nox"),
]

# Example manual-user account, created by an admin (Greg) for a player without Discord.
accounts.append(
    Account(next_id(), AccountType.MANUAL_USER, "Torvald (manual)", "Europe/Berlin",
            create_account_id=accounts[0].id)
)

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
          begin_date=date.today() + timedelta(days=1), end_date=date.today() + timedelta(days=3),
          qty_to_schedule=1, scheduled_start=datetime.utcnow() + timedelta(days=2), is_published=True),
    Event(next_id(), alliances[0].id, "Bear Trap", "Weekly bear trap coordination",
          begin_date=date.today(), end_date=date.today() + timedelta(days=7), qty_to_schedule=2),
    Event(next_id(), alliances[1].id, "Castle Battle", "Alliance castle defense",
          begin_date=date.today(), end_date=date.today() + timedelta(days=14)),
]

time_slots: list[TimeSlot] = [
    TimeSlot(next_id(), players[0].id, events[0].id,
             time(18, 0), time(20, 0), time_slot_type=TimeSlotType.PREFERRED),
    TimeSlot(next_id(), players[1].id, events[0].id,
             time(19, 0), time(21, 0), time_slot_type=TimeSlotType.ACCEPTABLE, needs_review=True),
    TimeSlot(next_id(), players[2].id, events[1].id,
             time(6, 0), time(7, 0), time_slot_type=TimeSlotType.AVOID),
]
