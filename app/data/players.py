"""
Player repository (`player` + `player_role` tables). Same conventions as
app/data/accounts.py: plain per-call SQLite queries, no in-memory mirror.

Roles are not an attribute of `Player` - they live in `player_role` and are
read via roles_by_player_id() below and written by passing `roles=` to
create_player() / update_player().
"""
from __future__ import annotations

from collections.abc import Collection
from datetime import datetime

from nicegui import run
from sqlmodel import delete, select

from app.db import get_session
from app.models.schema import Player, PlayerRole, Role, TimeSlot


def _list(account_ids: Collection[int] | None, alliance_ids: Collection[int] | None) -> list[Player]:
    query = select(Player).order_by(Player.player_id)
    if account_ids is not None:
        query = query.where(Player.account_id.in_(account_ids))
    if alliance_ids is not None:
        query = query.where(Player.alliance_id.in_(alliance_ids))
    with get_session() as session:
        return list(session.exec(query))


def _get(player_id: int) -> Player | None:
    with get_session() as session:
        return session.get(Player, player_id)


def _insert(player: Player, roles: list[Role]) -> Player:
    with get_session() as session:
        session.add(player)
        session.flush()  # assigns player_id
        session.add_all(PlayerRole(player_id=player.player_id, role=r) for r in set(roles))
        session.commit()
        session.refresh(player)
        return player


def _update(player_id: int, fields: dict, roles: list[Role] | None) -> Player:
    with get_session() as session:
        player = session.get(Player, player_id)
        if player is None:
            raise ValueError(f"No player with player_id={player_id}")
        for key, value in fields.items():
            setattr(player, key, value)
        if roles is not None:
            session.exec(delete(PlayerRole).where(PlayerRole.player_id == player_id))
            session.add_all(PlayerRole(player_id=player_id, role=r) for r in set(roles))
        session.add(player)
        session.commit()
        session.refresh(player)
        return player


def _delete(player_id: int) -> None:
    with get_session() as session:
        session.exec(delete(TimeSlot).where(TimeSlot.player_id == player_id))
        session.exec(delete(PlayerRole).where(PlayerRole.player_id == player_id))
        session.exec(delete(Player).where(Player.player_id == player_id))
        session.commit()


def _roles(player_ids: Collection[int] | None) -> dict[int, list[Role]]:
    query = select(PlayerRole)
    if player_ids is not None:
        query = query.where(PlayerRole.player_id.in_(player_ids))
    result: dict[int, list[Role]] = {}
    with get_session() as session:
        for row in session.exec(query):
            result.setdefault(row.player_id, []).append(row.role)
    return {pid: sorted(roles, key=list(Role).index) for pid, roles in result.items()}


async def list_players(
    *, account_ids: Collection[int] | None = None, alliance_ids: Collection[int] | None = None
) -> list[Player]:
    """Ordered by player_id. Each filter is skipped when None; an empty collection
    matches nothing (e.g. a viewer who belongs to no alliances)."""
    return await run.io_bound(_list, account_ids, alliance_ids)


async def get_player(player_id: int) -> Player | None:
    return await run.io_bound(_get, player_id)


async def create_player(
    *,
    account_id: int,
    alliance_id: int,
    kingshot_id: str,
    kingshot_name: str,
    power: int,
    town_center_level: str,
    discord_nickname: str | None = None,
    discord_guild_avatar_url: str | None = None,
    roles: list[Role] | None = None,
    create_account_id: int | None = None,
    update_account_id: int | None = None,
) -> Player:
    """`roles` defaults to [Role.USER]. `create_account_id` is None for self-adds
    (same convention as Account); `update_account_id` is always the acting account."""
    now = datetime.utcnow()
    player = Player(
        account_id=account_id,
        alliance_id=alliance_id,
        kingshot_id=kingshot_id,
        kingshot_name=kingshot_name,
        power=power,
        town_center_level=town_center_level,
        discord_nickname=discord_nickname,
        discord_guild_avatar_url=discord_guild_avatar_url,
        create_account_id=create_account_id,
        update_account_id=update_account_id,
        created_at=now,
        updated_at=now,
    )
    return await run.io_bound(_insert, player, roles or [Role.USER])


async def update_player(
    player_id: int, *, update_account_id: int | None, roles: list[Role] | None = None, **fields
) -> Player:
    """Updates whichever columns are passed in `fields`, plus the audit columns.
    `roles`, when given (not None), replaces the player's whole role set in the
    same transaction; None leaves roles untouched."""
    fields = {**fields, "update_account_id": update_account_id, "updated_at": datetime.utcnow()}
    return await run.io_bound(_update, player_id, fields, roles)


async def delete_player(player_id: int) -> None:
    """Removes the player along with its player_role and time_slot rows."""
    await run.io_bound(_delete, player_id)


async def roles_by_player_id(player_ids: Collection[int] | None = None) -> dict[int, list[Role]]:
    """One query for many players; players with no roles are simply absent from the dict."""
    return await run.io_bound(_roles, player_ids)

