"""
Time zone repository. Plain per-call SQLite queries - no in-memory mirror
(see app/data/accounts.py's module docstring for why).
"""
from __future__ import annotations

from nicegui import run
from sqlmodel import select

from app.db import get_session
from app.models.schema import TimeZone


def _list() -> list[TimeZone]:
    with get_session() as session:
        return list(session.exec(select(TimeZone).order_by(TimeZone.region, TimeZone.location)))


def _bulk_insert(rows: list[dict[str, str]]) -> None:
    with get_session() as session:
        session.add_all(TimeZone(region=row["region"], location=row["location"]) for row in rows)
        session.commit()


async def list_time_zones() -> list[TimeZone]:
    return await run.io_bound(_list)


async def bulk_create_time_zones(rows: list[dict[str, str]]) -> None:
    """Inserts one row per dict, each needing a "region" and "location" key -
    the shape the setup wizard's CSV upload produces."""
    await run.io_bound(_bulk_insert, rows)
