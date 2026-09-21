"""
Alliance repository. Same conventions as app/data/accounts.py: plain per-call
SQLite queries, no in-memory mirror.
"""
from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from nicegui import run
from sqlmodel import select

from app.db import get_session
from app.models.schema import Alliance


def _list(kingdom_ids: Collection[int] | None) -> list[Alliance]:
    query = select(Alliance).order_by(Alliance.alliance_id)
    if kingdom_ids is not None:
        query = query.where(Alliance.kingdom_id.in_(kingdom_ids))
    with get_session() as session:
        return list(session.exec(query))


def _get(alliance_id: int) -> Alliance | None:
    with get_session() as session:
        return session.get(Alliance, alliance_id)


def _insert(alliance: Alliance) -> Alliance:
    with get_session() as session:
        session.add(alliance)
        session.commit()
        session.refresh(alliance)
        return alliance


async def list_alliances(*, kingdom_ids: Collection[int] | None = None) -> list[Alliance]:
    """Ordered by alliance_id. `kingdom_ids` is skipped when None; an empty
    collection matches nothing."""
    return await run.io_bound(_list, kingdom_ids)


async def get_alliance(alliance_id: int) -> Alliance | None:
    return await run.io_bound(_get, alliance_id)


async def create_alliance(
    *,
    kingdom_id: int,
    name: str,
    discord_guild_id: str,
    discord_guild_name: str,
    create_account_id: int | None = None,
) -> Alliance:
    """Raises sqlalchemy.exc.IntegrityError if the kingdom doesn't exist, the name is
    already used within that kingdom, or the Discord guild already belongs to another alliance."""
    now = datetime.utcnow()
    alliance = Alliance(
        kingdom_id=kingdom_id,
        name=name,
        discord_guild_id=discord_guild_id,
        discord_guild_name=discord_guild_name,
        create_account_id=create_account_id,
        update_account_id=create_account_id,
        created_at=now,
        updated_at=now,
    )
    return await run.io_bound(_insert, alliance)
