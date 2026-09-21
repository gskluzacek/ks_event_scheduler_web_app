"""
Seeded fake data, held in module-level lists.

Everything in this file resets when the app restarts. It exists purely so the
mock UI has something believable to render, filter, and edit. When we move
past mocking, these lists get replaced by SQLite queries - the page code
should ideally not need to change much beyond the data-access layer.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.models.schema import Event, TimeSlot, TimeSlotType, TimeZone, next_id

time_zones: list[TimeZone] = [
    TimeZone(timezone_id=next_id(), region="America", location="New_York"),
    TimeZone(timezone_id=next_id(), region="America", location="Chicago"),
    TimeZone(timezone_id=next_id(), region="America", location="Los_Angeles"),
    TimeZone(timezone_id=next_id(), region="Europe", location="London"),
    TimeZone(timezone_id=next_id(), region="Europe", location="Berlin"),
    TimeZone(timezone_id=next_id(), region="Asia", location="Tokyo"),
    TimeZone(timezone_id=next_id(), region="Australia", location="Sydney"),
]

# Kingdom, Alliance, Account and Player are real SQLite tables now (app/data/). The events and
# time slots below still live here in memory, so they refer to alliances and players by the
# fixed ids that the seed scripts insert (run, in order, on a fresh DB:
# scripts.seed_preview_accounts, scripts.seed_preview_kingdoms_alliances, scripts.seed_preview_players).
_ALLIANCE_ID_SHD = 2001  # [SHD] Shadow Stooges - scripts/preview_kingdoms_alliances.yaml
_ALLIANCE_ID_PHX = 2002  # [PHX] Dark Phoenix Rising
# Player ids (scripts/preview_players.yaml) that the time slots below belong to.
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
        alliance_id=_ALLIANCE_ID_SHD,
        name="[BT] Bear Hunt",
        description="EOD bear trap",
        begin_date=date.today() - timedelta(days=28),
        end_date=date.today() + timedelta(days=28),
        qty_to_schedule=2,
        is_published=True,
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_SHD,
        name="[KvK] Kingdom vs Kingdom",
        description="Cross-kingdom war window",
        begin_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=3),
        scheduled_start=datetime.utcnow() + timedelta(days=2),  # noqa
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_PHX,
        name="[CB] Castle Battle",
        description="Alliance castle defense",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_PHX,
        name="[SS] Swordland Showdown",
        description="Win the ancient Sword of Kings and rule the realm",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_PHX,
        name="[TAC] Tri-Alliance Clash",
        description="Maritime battle for the Temple Of Tides",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_PHX,
        name="[ACh] Alliance Championship",
        description="Three lane round-robin 5 round tournament",
        begin_date=date.today(),
        end_date=date.today() + timedelta(days=14),
    ),
    Event(
        id=next_id(),
        alliance_id=_ALLIANCE_ID_PHX,
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
