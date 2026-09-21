"""
Event repository. Same conventions as app/data/accounts.py: plain per-call
SQLite queries, no in-memory mirror.
"""
from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime

from nicegui import run
from sqlmodel import select

from app.db import get_session
from app.models.schema import Event


def _list(alliance_ids: Collection[int] | None) -> list[Event]:
    query = select(Event).order_by(Event.event_id)
    if alliance_ids is not None:
        query = query.where(Event.alliance_id.in_(alliance_ids))
    with get_session() as session:
        return list(session.exec(query))


def _get(event_id: int) -> Event | None:
    with get_session() as session:
        return session.get(Event, event_id)


def _insert(event: Event) -> Event:
    with get_session() as session:
        session.add(event)
        session.commit()
        session.refresh(event)
        return event


def _update(event_id: int, fields: dict) -> Event:
    with get_session() as session:
        event = session.get(Event, event_id)
        if event is None:
            raise ValueError(f"No event with event_id={event_id}")
        for key, value in fields.items():
            setattr(event, key, value)
        session.add(event)
        session.commit()
        session.refresh(event)
        return event


async def list_events(*, alliance_ids: Collection[int] | None = None) -> list[Event]:
    """Ordered by event_id. `alliance_ids` is skipped when None; an empty collection matches nothing."""
    return await run.io_bound(_list, alliance_ids)


async def get_event(event_id: int) -> Event | None:
    return await run.io_bound(_get, event_id)


async def create_event(
    *,
    alliance_id: int,
    event_name: str,
    event_desc: str = "",
    begin_date: date | None = None,
    end_date: date | None = None,
    qty_to_schedule: int = 1,
    active_ind: bool = True,
    create_account_id: int | None = None,
) -> Event:
    """Raises sqlalchemy.exc.IntegrityError if the alliance doesn't exist, the name is already used
    within that alliance, begin_date is after end_date, or qty_to_schedule < 1."""
    now = datetime.utcnow()
    event = Event(
        alliance_id=alliance_id,
        event_name=event_name,
        event_desc=event_desc,
        begin_date=begin_date,
        end_date=end_date,
        qty_to_schedule=qty_to_schedule,
        active_ind=active_ind,
        create_account_id=create_account_id,
        update_account_id=create_account_id,
        created_at=now,
        updated_at=now,
    )
    return await run.io_bound(_insert, event)


async def update_event(event_id: int, *, update_account_id: int | None, **fields) -> Event:
    """Updates whichever columns are passed in `fields`, plus the audit columns."""
    fields = {**fields, "update_account_id": update_account_id, "updated_at": datetime.utcnow()}
    return await run.io_bound(_update, event_id, fields)
