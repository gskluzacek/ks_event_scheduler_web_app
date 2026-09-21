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
    Event, SampleAlliance, SampleKingdom, TimeSlot,
    TimeSlotType, TimeZone, next_id,
)

time_zones: list[TimeZone] = [
    TimeZone(timezone_id=next_id(), region="America", location="New_York"),
    TimeZone(timezone_id=next_id(), region="America", location="Chicago"),
    TimeZone(timezone_id=next_id(), region="America", location="Los_Angeles"),
    TimeZone(timezone_id=next_id(), region="Europe", location="London"),
    TimeZone(timezone_id=next_id(), region="Europe", location="Berlin"),
    TimeZone(timezone_id=next_id(), region="Asia", location="Tokyo"),
    TimeZone(timezone_id=next_id(), region="Australia", location="Sydney"),
]

# Kingdom ids are pinned literals (4001-4002) for the same reason as the alliance ids below:
# the `kingdom` and `alliance` tables are seeded (scripts/seed_preview_kingdoms_alliances.py)
# from scripts/preview_kingdoms_alliances.yaml with these same ids - keep the two in sync.
kingdoms: list[SampleKingdom] = [
    SampleKingdom(4001, "#1542"),
    SampleKingdom(4002, "#1467"),
]

# Alliance ids are pinned literals (2001-2006), not next_id(): the `player` table's
# alliance_id is a real FK to the seeded `alliance` table, so scripts/preview_players.yaml
# refers to them by these fixed values. Same trick as account_id 1001-1005.
# Only the FIRST alliance (2001) has a real guild - Greg's corn-bot-1 is already a member, so it
# exercises the actual bot-token guild-membership check end to end (see auth/discord_guild.py).
# The other five use obviously-fake guild ids, because discord_guild_id is UNIQUE in the
# `alliance` table (one guild per alliance) - verification against them is expected to fail,
# which doubles as the negative test. Keep in sync with scripts/preview_kingdoms_alliances.yaml.
alliances: list[SampleAlliance] = [
    SampleAlliance(
        id=2001,            # index 0
        name="[SHD] Shadow Stooges",
        kingdom_id=kingdoms[0].id,
        discord_guild_id="1517613215138189444",
        discord_guild_name="Dark Lords of the Shadow Realm"
    ),
    SampleAlliance(
        id=2002,            # index 1
        name="[PHX] Dark Phoenix Rising",
        kingdom_id=kingdoms[0].id,
        discord_guild_id="900000000000002002",
        discord_guild_name="Mister Mojo Risin'"
    ),
    SampleAlliance(
        id=2003,            # index 2
        name="[UFC] Ultimate Fighting Clan",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="900000000000002003",
        discord_guild_name="Drink Clamoto Juice and Live!"
    ),
    SampleAlliance(
        id=2004,            # index 3
        name="[UMP] Umbra Pickles",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="900000000000002004",
        discord_guild_name="NOT Magic: The Gathering"
    ),
    SampleAlliance(
        id=2005,            # index 4
        name="[sOS] Hospitable Canteen",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="900000000000002005",
        discord_guild_name="Same Old Shit"
    ),
    SampleAlliance(
        id=2006,            # index 5
        name="[STN] Silent Thunder and Nonsense",
        kingdom_id=kingdoms[1].id,
        discord_guild_id="900000000000002006",
        discord_guild_name="Silent But Not So Deadly"
    ),
]

# Account and Player are real SQLite tables now (app/data/accounts.py, app/data/players.py).
# The time slots below still live here in memory, so they refer to their players by the
# fixed player_id values that scripts/preview_players.yaml seeds (run
# scripts.seed_preview_accounts, then scripts.seed_preview_players, on a fresh DB).
_PLAYER_ID_DARK_CHOCOLATE = 3001
_PLAYER_ID_MILK_CHOCOLATE = 3002
_PLAYER_ID_MINT_CHOCOLATE = 3003
_PLAYER_ID_MOUTHY_MARLA = 3009
_PLAYER_ID_JACKS_ANGRY_SPLEAN = 3010
_PLAYER_ID_DESERT_MOON = 3011
_PLAYER_ID_SCHRODINGERS_CAT = 3012

events: list[Event] = [
    Event(
        id=next_id(),
        alliance_id=alliances[0].id,
        name="[BT] Bear Hunt",
        description="EOD bear trap",
        begin_date=date.today() - timedelta(days=28),
        end_date=date.today() + timedelta(days=28),
        qty_to_schedule=2,
        is_published=True,
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[0].id,
        name="[KvK] Kingdom vs Kingdom",
        description="Cross-kingdom war window",
        begin_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=3),
        scheduled_start=datetime.utcnow() + timedelta(days=2),  # noqa
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[1].id,
        name="[CB] Castle Battle",
        description="Alliance castle defense",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[1].id,
        name="[SS] Swordland Showdown",
        description="Win the ancient Sword of Kings and rule the realm",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[1].id,
        name="[TAC] Tri-Alliance Clash",
        description="Maritime battle for the Temple Of Tides",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[1].id,
        name="[ACh] Alliance Championship",
        description="Three lane round-robin 5 round tournament",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=alliances[1].id,
        name="[SncB] Sanctuary Battle",
        description="Defeat the Cesares Rebels in the Sanctuary",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
]

time_slots: list[TimeSlot] = [
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DARK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(8, 0),
        local_end=time(17, 15),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DARK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(17, 15),
        local_end=time(18, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DARK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(18, 0),
        local_end=time(19, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DARK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(19, 0),
        local_end=time(00, 0),
    ),

    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MILK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(19, 0),
        local_end=time(21, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
        needs_review=True,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MILK_CHOCOLATE,
        event_id=events[0].id,
        local_start=time(22, 0),
        local_end=time(23, 0),
        time_slot_type=TimeSlotType.PREFERRED,
        needs_review=True,
    ),

    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MINT_CHOCOLATE,
        event_id=events[1].id,
        local_start=time(6, 0),
        local_end=time(7, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MINT_CHOCOLATE,
        event_id=events[1].id,
        local_start=time(7, 0),
        local_end=time(8, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),





    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MOUTHY_MARLA,
        event_id=events[1].id,
        local_start=time(6, 0),
        local_end=time(7, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_MOUTHY_MARLA,
        event_id=events[1].id,
        local_start=time(7, 0),
        local_end=time(8, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),

    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_JACKS_ANGRY_SPLEAN,
        event_id=events[1].id,
        local_start=time(6, 0),
        local_end=time(7, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_JACKS_ANGRY_SPLEAN,
        event_id=events[1].id,
        local_start=time(7, 0),
        local_end=time(8, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),

    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DESERT_MOON,
        event_id=events[1].id,
        local_start=time(6, 0),
        local_end=time(7, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_DESERT_MOON,
        event_id=events[1].id,
        local_start=time(7, 0),
        local_end=time(8, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),

    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_SCHRODINGERS_CAT,
        event_id=events[1].id,
        local_start=time(6, 0),
        local_end=time(7, 0),
        time_slot_type=TimeSlotType.AVOID,
    ),
    TimeSlot(
        id=next_id(),
        player_id=_PLAYER_ID_SCHRODINGERS_CAT,
        event_id=events[1].id,
        local_start=time(7, 0),
        local_end=time(8, 0),
        time_slot_type=TimeSlotType.ACCEPTABLE,
    ),
]
