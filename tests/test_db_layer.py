"""The database layer, without any page: preview seeds, enforced foreign keys, CHECK/UNIQUE constraints, the
no-overlap triggers on time_slot, and the repositories in app/data/."""
from datetime import date, time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

import app.db as app_db
from app.data import alliances, events, kingdoms, players, time_slots
from app.data.time_slots import TimeSlotOverlapError
from app.models.schema import Alliance, Event, Kingdom, Player, TimeSlot, TimeSlotType
from scripts import (
    seed_preview_accounts, seed_preview_events_time_slots, seed_preview_kingdoms_alliances, seed_preview_players,
)
from tests.conftest import make_engine, seed_preview_data


def count(model) -> int:
    with app_db.get_session() as session:
        return len(session.exec(select(model)).all())


def slot(**overrides) -> TimeSlot:
    """A valid slot for player 3001 / event 5001 at a free time of day, with any field overridden."""
    fields = dict(event_id=5001, player_id=3001, tslot_type=TimeSlotType.AVOID,
                  start_time=time(1, 0), end_time=time(1, 14, 59))
    return TimeSlot(**{**fields, **overrides})


# ------------------------------------------------------------------ seeds
def test_seeds_load_the_expected_rows():
    assert (count(Kingdom), count(Alliance), count(Player), count(Event), count(TimeSlot)) == (2, 6, 12, 7, 16)


def test_seeds_are_idempotent():
    before = (count(Kingdom), count(Alliance), count(Player), count(Event), count(TimeSlot))
    seed_preview_data()
    assert (count(Kingdom), count(Alliance), count(Player), count(Event), count(TimeSlot)) == before


def test_seed_end_times_use_the_minus_one_second_convention():
    with app_db.get_session() as session:
        by_id = {s.tslot_id: s for s in session.exec(select(TimeSlot)).all()}
    assert (by_id[6001].start_time, by_id[6001].end_time) == (time(8, 0), time(17, 14, 59))
    assert by_id[6004].end_time == time(23, 59, 59)                       # was 00:00 - midnight
    assert {t.tslot_id for t in by_id.values() if not t.confirmed_ind} == {6005, 6006}


def test_seed_scripts_refuse_to_run_out_of_order(tmp_path, monkeypatch):
    monkeypatch.setattr(app_db, "engine", make_engine(tmp_path / "empty.db"))
    seed_preview_accounts.seed()
    with pytest.raises(SystemExit, match="seed_preview_kingdoms_alliances"):
        seed_preview_players.seed()                                       # players need alliances first
    seed_preview_kingdoms_alliances.seed()
    with pytest.raises(SystemExit, match="seed_preview_players"):
        seed_preview_events_time_slots.seed()                             # slots need players first


# ------------------------------------------------------------------ constraints
def test_foreign_keys_are_enforced():
    with app_db.get_session() as session:
        assert session.exec(text("PRAGMA foreign_keys")).first() == (1,)


REJECTED = {
    "kingdom: duplicate name": lambda s: s.add(Kingdom(name="#1542")),
    "alliance: unknown kingdom": lambda s: s.add(Alliance(kingdom_id=99999, name="n", discord_guild_id="g1", discord_guild_name="n")),
    "alliance: guild already used": lambda s: s.add(Alliance(kingdom_id=4001, name="n2", discord_guild_id="1517613215138189444", discord_guild_name="n")),
    "alliance: name reused in the kingdom": lambda s: s.add(Alliance(kingdom_id=4001, name="[SHD] Shadow Stooges", discord_guild_id="g2", discord_guild_name="n")),
    "player: unknown alliance": lambda s: s.add(Player(account_id=1001, alliance_id=99999, kingshot_id="x", kingshot_name="x", power=1, town_center_level="1")),
    "event: duplicate name in alliance": lambda s: s.add(Event(alliance_id=2001, event_name="[BT] Bear Hunt")),
    "event: begin after end": lambda s: s.add(Event(alliance_id=2001, event_name="X", begin_date=date(2026, 2, 2), end_date=date(2026, 2, 1))),
    "event: quantity 0": lambda s: s.add(Event(alliance_id=2001, event_name="Y", qty_to_schedule=0)),
    "event: unknown alliance": lambda s: s.add(Event(alliance_id=99999, event_name="Z")),
    "time_slot: end equals start": lambda s: s.add(slot(start_time=time(5, 0), end_time=time(5, 0))),
    "time_slot: end before start": lambda s: s.add(slot(start_time=time(5, 0), end_time=time(4, 0))),
    "time_slot: priority 0": lambda s: s.add(slot(priority=0)),
    "time_slot: unknown event": lambda s: s.add(slot(event_id=99999)),
    "time_slot: unknown player": lambda s: s.add(slot(player_id=99999)),
    "time_slot: bad type (raw SQL)": lambda s: s.exec(text(
        "insert into time_slot (event_id,player_id,tslot_type,start_time,end_time,confirmed_ind,created_at,updated_at) "
        "values (5001,3001,'bogus','01:00:00','01:14:59',1,'2026-01-01','2026-01-01')")),
}


@pytest.mark.parametrize("build", REJECTED.values(), ids=REJECTED.keys())
def test_database_rejects(build):
    with app_db.get_session() as session:
        with pytest.raises(IntegrityError):
            build(session)          # raw-SQL cases fail here, ORM adds fail on commit
            session.commit()


def test_valid_rows_are_accepted():
    with app_db.get_session() as session:
        session.add(slot(priority=1))
        session.add(Event(alliance_id=2001, event_name="Fine", begin_date=date(2026, 1, 1), end_date=date(2026, 1, 1)))
        session.commit()


# ------------------------------------------------------------------ no-overlap triggers
# Player 3001 / event 5001 has these seeded slots (6001-6004): 08:00:00-17:14:59, 17:15:00-17:59:59,
# 18:00:00-18:59:59 and 19:00:00-23:59:59. Only 00:00:00-07:59:59 is free.
@pytest.mark.parametrize("start, end", [
    (time(9, 0), time(10, 0)),               # inside it
    (time(7, 0), time(8, 0)),                # straddles its start
    (time(17, 0), time(18, 0)),              # straddles its end
    (time(17, 14, 59), time(17, 30, 0)),     # touches its last second
    (time(6, 0), time(18, 0)),               # contains it
])
def test_overlapping_slot_is_rejected_even_by_raw_sql(start, end):
    with app_db.get_session() as session:
        session.add(slot(start_time=start, end_time=end))
        with pytest.raises(IntegrityError, match="time_slot overlaps"):
            session.commit()


def test_adjacent_slot_and_other_player_or_event_are_allowed():
    with app_db.get_session() as session:
        session.add(slot(start_time=time(7, 0), end_time=time(7, 59, 59)))         # ends the second before 6001 starts
        session.add(slot(event_id=5002, start_time=time(8, 0), end_time=time(9, 0)))   # same times, other event
        session.add(slot(player_id=3009, start_time=time(8, 0), end_time=time(9, 0)))  # same times, other player
        session.commit()


def test_update_into_an_overlap_is_rejected_but_updating_a_slots_own_range_is_fine():
    with app_db.get_session() as session:
        first = session.get(TimeSlot, 6001)
        first.end_time = time(16, 59, 59)                  # shrink itself: fine
        session.commit()
        moved = TimeSlot(event_id=5001, player_id=3001, start_time=time(1, 0), end_time=time(1, 59, 59))
        session.add(moved)
        session.commit()
        moved.end_time = time(8, 30)                       # now runs into 6001
        with pytest.raises(IntegrityError, match="time_slot overlaps"):
            session.commit()


# ------------------------------------------------------------------ repositories
async def test_time_slot_repo_reports_overlaps_and_keeps_the_row_unchanged():
    created = await time_slots.create_time_slot(
        event_id=5001, player_id=3001, start_time=time(0, 0), end_time=time(7, 44, 59),
        create_account_id=1001, update_account_id=1001)
    assert (created.confirmed_ind, created.priority, created.tslot_type) == (True, None, TimeSlotType.PREFERRED)
    with pytest.raises(TimeSlotOverlapError, match="overlaps"):
        await time_slots.create_time_slot(
            event_id=5001, player_id=3001, start_time=time(8, 30), end_time=time(8, 59, 59), update_account_id=1001)
    with pytest.raises(TimeSlotOverlapError):
        await time_slots.update_time_slot(created.tslot_id, update_account_id=1001, end_time=time(8, 30))
    assert (await time_slots.get_time_slot(created.tslot_id)).end_time == time(7, 44, 59)
    updated = await time_slots.update_time_slot(created.tslot_id, update_account_id=1002, confirmed_ind=False)
    assert (updated.confirmed_ind, updated.update_account_id) == (False, 1002)


async def test_time_slot_repo_list_and_count():
    assert len(await time_slots.list_time_slots()) == 16
    assert len(await time_slots.list_time_slots(player_ids=[3001])) == 4
    assert await time_slots.list_time_slots(player_ids=[]) == []
    assert {s.event_id for s in await time_slots.list_time_slots(event_ids=[5002])} == {5002}
    assert await time_slots.count_time_slots_by_player([3001, 3002, 3012]) == {3001: 4, 3002: 2, 3012: 2}
    assert sum((await time_slots.count_time_slots_by_player()).values()) == 16


async def test_event_repo():
    created = await events.create_event(alliance_id=2001, event_name="[NEW] Test", qty_to_schedule=2, create_account_id=1001)
    assert (created.event_desc, created.active_ind, created.is_published, created.update_account_id) == ("", True, False, 1001)
    updated = await events.update_event(created.event_id, update_account_id=1002, is_published=True, event_desc="d")
    assert (updated.is_published, updated.event_desc, updated.update_account_id) == (True, "d", 1002)
    assert len(await events.list_events(alliance_ids=[2002])) == 5
    assert await events.list_events(alliance_ids=[]) == []
    assert (await events.get_event(99999)) is None
    with pytest.raises(IntegrityError):
        await events.create_event(alliance_id=2001, event_name="[NEW] Test")


async def test_kingdom_and_alliance_repos():
    kingdom = await kingdoms.create_kingdom(name="#9999", create_account_id=1001)
    alliance = await alliances.create_alliance(
        kingdom_id=kingdom.kingdom_id, name="[NEW] New", discord_guild_id="123", discord_guild_name="New", create_account_id=1001)
    assert (alliance.update_account_id, (await alliances.get_alliance(alliance.alliance_id)).name) == (1001, "[NEW] New")
    assert [a.alliance_id for a in await alliances.list_alliances(kingdom_ids=[4002])] == [2003, 2004, 2005, 2006]
    assert await alliances.list_alliances(kingdom_ids=[]) == []
    with pytest.raises(IntegrityError):
        await alliances.create_alliance(kingdom_id=kingdom.kingdom_id, name="x", discord_guild_id="123", discord_guild_name="x")


async def test_deleting_a_player_removes_their_slots_and_roles():
    assert (await time_slots.count_time_slots_by_player([3001]))[3001] == 4
    await players.delete_player(3001)
    assert await time_slots.count_time_slots_by_player([3001]) == {}
    assert await players.get_player(3001) is None
    assert (await players.roles_by_player_id([3001])) == {}
