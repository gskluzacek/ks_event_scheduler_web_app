"""
Account repository. Plain per-call SQLite queries - no in-memory mirror (see
app/data/__init__.py: each function reads/writes exactly what its caller
needs, right when it's called, same as any other DB-backed page will once
migrated).
"""
from __future__ import annotations

from datetime import datetime

from nicegui import run
from sqlmodel import select

from app.db import get_session
from app.models.schema import Account, AccountType


def _has_any() -> bool:
    with get_session() as session:
        return session.exec(select(Account).limit(1)).first() is not None


def _insert(account: Account) -> Account:
    with get_session() as session:
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


async def has_any_account() -> bool:
    return await run.io_bound(_has_any)


async def create_account(
    *,
    account_type: AccountType,
    account_name: str,
    time_zone: str,
    is_super_admin: bool = False,
    create_account_id: int | None = None,
    **discord_fields,
) -> Account:
    """`discord_fields` covers the AccountType.DISCORD_USER-only columns
    (discord_user_id, discord_username, discord_global_name, discord_avatar_url,
    discord_access_token, discord_refresh_token, discord_token_expires_at) -
    omit them entirely for a manual-user account."""
    now = datetime.utcnow()
    account = Account(
        account_type=account_type,
        account_name=account_name,
        time_zone=time_zone,
        is_super_admin=is_super_admin,
        create_account_id=create_account_id,
        update_account_id=create_account_id,
        created_at=now,
        updated_at=now,
        **discord_fields,
    )
    return await run.io_bound(_insert, account)
