"""
Time slot repository. Same conventions as app/data/accounts.py: plain per-call
SQLite queries, no in-memory mirror.

`end_time` is the picked end minus one second (see schema.TimeSlot) - this layer stores
exactly what it is given; the UI does the +/-1 second conversion for display/entry.
"""
from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, time

from nicegui import run
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.db import get_session
from app.models.schema import TimeSlot, TimeSlotType


class TimeSlotOverlapError(ValueError):
    """The slot would overlap another slot for the same player and event (rejected by the
    no-overlap triggers in app/models/schema.py)."""


def _commit(session, slot: TimeSlot) -> TimeSlot:
    session.add(slot)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        if "time_slot overlaps" in str(e.orig):
            raise TimeSlotOverlapError(
                "This time slot overlaps another slot for the same player and event."
            ) from e
        raise
    session.refresh(slot)
    return slot


def _list(player_ids: Collection[int] | None, event_ids: Collection[int] | None) -> list[TimeSlot]:
    query = select(TimeSlot).order_by(TimeSlot.tslot_id)
    if player_ids is not None:
        query = query.where(TimeSlot.player_id.in_(player_ids))
    if event_ids is not None:
        query = query.where(TimeSlot.event_id.in_(event_ids))
    with get_session() as session:
        return list(session.exec(query))


def _get(tslot_id: int) -> TimeSlot | None:
    with get_session() as session:
        return session.get(TimeSlot, tslot_id)


def _insert(slot: TimeSlot) -> TimeSlot:
    with get_session() as session:
        return _commit(session, slot)


def _update(tslot_id: int, fields: dict) -> TimeSlot:
    with get_session() as session:
        slot = session.get(TimeSlot, tslot_id)
        if slot is None:
            raise ValueError(f"No time slot with tslot_id={tslot_id}")
        for key, value in fields.items():
            setattr(slot, key, value)
        return _commit(session, slot)


def _count_by_player(player_ids: Collection[int] | None) -> dict[int, int]:
    query = select(TimeSlot.player_id, func.count()).group_by(TimeSlot.player_id)
    if player_ids is not None:
        query = query.where(TimeSlot.player_id.in_(player_ids))
    with get_session() as session:
        return {player_id: count for player_id, count in session.exec(query)}


async def list_time_slots(
    *, player_ids: Collection[int] | None = None, event_ids: Collection[int] | None = None
) -> list[TimeSlot]:
    """Ordered by tslot_id. Each filter is skipped when None; an empty collection matches nothing."""
    return await run.io_bound(_list, player_ids, event_ids)


async def get_time_slot(tslot_id: int) -> TimeSlot | None:
    return await run.io_bound(_get, tslot_id)


async def count_time_slots_by_player(player_ids: Collection[int] | None = None) -> dict[int, int]:
    """One grouped query; players with no slots are simply absent from the dict."""
    return await run.io_bound(_count_by_player, player_ids)


async def create_time_slot(
    *,
    event_id: int,
    player_id: int,
    start_time: time,
    end_time: time,
    tslot_type: TimeSlotType = TimeSlotType.PREFERRED,
    priority: int | None = None,
    confirmed_ind: bool = True,
    create_account_id: int | None = None,
    update_account_id: int | None = None,
) -> TimeSlot:
    """`create_account_id` is None for a slot its owner adds themselves (same convention as
    Account/Player); `update_account_id` is always the acting account. Raises TimeSlotOverlapError
    if it overlaps another slot for the same player and event, and IntegrityError for the other
    constraints (unknown player/event, end_time <= start_time, ...)."""
    now = datetime.utcnow()
    slot = TimeSlot(
        event_id=event_id,
        player_id=player_id,
        start_time=start_time,
        end_time=end_time,
        tslot_type=tslot_type,
        priority=priority,
        confirmed_ind=confirmed_ind,
        create_account_id=create_account_id,
        update_account_id=update_account_id,
        created_at=now,
        updated_at=now,
    )
    return await run.io_bound(_insert, slot)


async def update_time_slot(tslot_id: int, *, update_account_id: int | None, **fields) -> TimeSlot:
    """Updates whichever columns are passed in `fields`, plus the audit columns.
    Raises TimeSlotOverlapError like create_time_slot()."""
    fields = {**fields, "update_account_id": update_account_id, "updated_at": datetime.utcnow()}
    return await run.io_bound(_update, tslot_id, fields)
