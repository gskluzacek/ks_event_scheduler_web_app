"""
Seeded fake data, held in module-town_center_level lists.

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
    Kingdom(next_id(), "#1542"),
    Kingdom(next_id(), "#1467"),
]

# Real guild - Greg's corn-bot-1 is already a member, so this alliance can exercise the
# actual bot-token guild-membership check end to end (see auth/discord_guild.py).
alliances: list[Alliance] = [
    Alliance(
        id=next_id(),
        name="[SHD] Shadow Stooges",
        kingdom_id=kingdoms[0].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Dark Lords of the Shadow Realm"
    ),
    Alliance(
        id=next_id(),
        name="[PHX] Dark Phoenix Rising]",
        kingdom_id=kingdoms[0].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Mister Mojo Risin'"
    ),
    Alliance(
        id=next_id(),
        name="[UFC] Ultimate Fighting Clan]",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Drink Clamoto Juice and Live!"
    ),
    Alliance(
        id=next_id(),
        name="[UMP] Umbra Pickles]",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="NOT Magic: The Gathering"
    ),
    Alliance(
        id=next_id(),
        name="[sOS] Hospitable Canteen]",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Same Old Shit"
    ),
    Alliance(
        id=next_id(),
        name="[STN] Silent Thunder and Nonsense]",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Silent But Not So Deadly"
    ),
]

accounts: list[Account] = [
    Account(
        id=next_id(),
        account_type=AccountType.DISCORD_USER,
        account_name="gskluzacek",
        time_zone="America/Chicago",
        discord_user_id="835177531904098380",
        discord_username="gskluzacek",
        discord_global_name="Greg",
        is_super_admin=True,
    ),
    Account(
        id=next_id(),
        account_type=AccountType.DISCORD_USER,
        account_name="marla_singer_2026",
        time_zone="America/New_York",
        discord_user_id="222222222222222222",
        discord_username="marla_singer_2026",
        discord_global_name="Marla Singer",
    ),
    Account(
        id=next_id(),
        account_type=AccountType.DISCORD_USER,
        account_name="tyler_durden_58",
        time_zone="Europe/London",
        discord_user_id="333333333333333333",
        discord_username="tyler_durden_58",
        discord_global_name="Tyler Durden",
    ),
    Account(
        id=next_id(),
        account_type=AccountType.DISCORD_USER,
        account_name="mr_roboto_1983",
        time_zone="Asia/Tokyo",
        discord_user_id="444444444444444444",
        discord_username="mr_roboto_1983",
        discord_global_name="Kilroy",
    ),
]

# Example manual-user account, created by an admin (Greg) for a player without Discord.
accounts.append(
    Account(
        id=next_id(),
        account_type=AccountType.MANUAL_USER,
        account_name="max_manual_planck",
        time_zone="Europe/Berlin",
        create_account_id=accounts[0].id
    )
)

players: list[Player] = [
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[0].id,
        kingshot_id="229989369",
        kingshot_name="Dark Chocolate",
        discord_nickname="The Dark 'Chocolate' Knight",
        power=131200000,
        town_center_level=30,
        roles=[Role.POWER_ADMIN],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[0].id,
        kingshot_id="229989370",
        kingshot_name="Milk Chocolate",
        discord_nickname="Count Chocula",
        power=131200001,
        town_center_level=21,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[1].id,
        kingshot_id="229989371",
        kingshot_name="Mint Chocolate",
        discord_nickname="Luck O' The Irish",
        power=131200002,
        town_center_level=22,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[1].id,
        kingshot_id="229989372",
        kingshot_name="White Chocolate",
        discord_nickname="I'm not a bigot, honestly",
        power=131200003,
        town_center_level=23,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[1].id,
        kingshot_id="229989373",
        kingshot_name="Unsweetened Chocolate",
        discord_nickname="Just a bitter Old Man",
        power=131200004,
        town_center_level=24,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[2].id,
        kingshot_id="229989374",
        kingshot_name="German Chocolate",
        discord_nickname="Not zi from Germany",
        power=131200005,
        town_center_level=25,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[2].id,
        kingshot_id="229989375",
        kingshot_name="Mexican Chocolate",
        discord_nickname="Ima SOOO Spicy ¡Olé!",
        power=131200006,
        town_center_level=26,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[0].id,
        alliance_id=alliances[2].id,
        kingshot_id="229989376",
        kingshot_name="Hazelnut Chocolate",
        discord_nickname="Better than Nutella",
        power=131200007,
        town_center_level=27,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[1].id,
        alliance_id=alliances[3].id,
        kingshot_id="999666333",
        kingshot_name="Mouthy Marla",
        discord_nickname="Bride of Tyler Durden",
        power=61250,
        town_center_level=19,
        roles=[Role.ADMIN],
    ),
    Player(
        id=next_id(),
        account_id=accounts[2].id,
        alliance_id=alliances[3].id,
        kingshot_id="222555888",
        kingshot_name="Jack's Angry Splean",
        discord_nickname="Tyler Durden",
        power=45300,
        town_center_level=22,
        roles=[Role.SCHEDULER_ADMIN],
    ),
    Player(
        id=next_id(),
        account_id=accounts[3].id,
        alliance_id=alliances[4].id,
        kingshot_id="111444777",
        kingshot_name="Desert Moon",
        discord_nickname="Dennis DeYoung Poser",
        power=39900,
        town_center_level=20,
        roles=[Role.USER],
    ),
    Player(
        id=next_id(),
        account_id=accounts[3].id,
        alliance_id=alliances[4].id,
        kingshot_id="314159265",
        kingshot_name="h = 6.62607015",
        discord_nickname="Schrödinger’s Cat",
        power=39900,
        town_center_level=20,
        roles=[Role.USER],
    ),
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
