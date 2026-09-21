"""
Kingdom repository. Plain per-call SQLite queries - no in-memory mirror
(see app/data/accounts.py's module docstring for why).
"""
from __future__ import annotations

from datetime import datetime

from nicegui import run
from sqlmodel import select

from app.db import get_session
from app.models.schema import Kingdom


def _list() -> list[Kingdom]:
    with get_session() as session:
        return list(session.exec(select(Kingdom).order_by(Kingdom.kingdom_id)))


def _get(kingdom_id: int) -> Kingdom | None:
    with get_session() as session:
        return session.get(Kingdom, kingdom_id)


def _insert(kingdom: Kingdom) -> Kingdom:
    with get_session() as session:
        session.add(kingdom)
        session.commit()
        session.refresh(kingdom)
        return kingdom


async def list_kingdoms() -> list[Kingdom]:
    return await run.io_bound(_list)


async def get_kingdom(kingdom_id: int) -> Kingdom | None:
    return await run.io_bound(_get, kingdom_id)


async def create_kingdom(*, name: str, create_account_id: int | None = None) -> Kingdom:
    """Raises sqlalchemy.exc.IntegrityError if `name` is already taken."""
    now = datetime.utcnow()
    kingdom = Kingdom(
        name=name,
        create_account_id=create_account_id,
        update_account_id=create_account_id,
        created_at=now,
        updated_at=now,
    )
    return await run.io_bound(_insert, kingdom)
