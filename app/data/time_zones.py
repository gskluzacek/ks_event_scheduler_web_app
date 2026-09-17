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


def _bulk_insert(rows: list[dict[str, str]]) -> int:
    with get_session() as session:
        existing = {(z.region, z.location) for z in session.exec(select(TimeZone))}
        unique_rows = {(r["region"], r["location"]): r for r in rows}
        new_zones = [
            TimeZone(region=region, location=location)
            for region, location in unique_rows
            if (region, location) not in existing
        ]
        session.add_all(new_zones)
        session.commit()
        return len(new_zones)


async def list_time_zones() -> list[TimeZone]:
    return await run.io_bound(_list)


async def bulk_create_time_zones(rows: list[dict[str, str]]) -> int:
    """Inserts one row per dict, each needing a "region" and "location" key -
    the shape the setup wizard's CSV upload produces. Skips any pair already
    in the table (or repeated within this same batch) rather than erroring
    on the region+location unique constraint; returns how many were actually
    inserted."""
    return await run.io_bound(_bulk_insert, rows)
