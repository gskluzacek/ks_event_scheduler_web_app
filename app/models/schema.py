"""
In-memory data model for the mock phase.

NOTE: These are plain dataclasses in module-level lists, acting as a stand-in
for the eventual SQLite tables (see web_app_requirements.md > Data Model Overview).
Module-level state is normally an anti-pattern in NiceGUI (shared across all
users - see nicegui_llms.md Mental Model #2), but for this mock every "user"
is really just us previewing roles, so a shared in-memory store is fine and
even useful (edits by one role are visible when you switch roles).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from itertools import count
from zoneinfo import ZoneInfo

_id_counter = count(1)


def next_id() -> int:
    return next(_id_counter)


class Role(str, Enum):
    USER = "User"
    ADMIN = "Admin"
    POWER_ADMIN = "PowerAdmin"
    SCHEDULER_ADMIN = "SchedulerAdmin"
    SUPER_ADMIN = "SuperAdmin"  # account-level, not tied to an alliance


class AccountType(str, Enum):
    DISCORD_USER = "discord-user"
    MANUAL_USER = "manual-user"


class TimeSlotType(str, Enum):
    PREFERRED = "preferred"
    ACCEPTABLE = "acceptable"
    AVOID = "avoid"


@dataclass
class TimeZone:
    """Just the IANA name - no stored UTC offset (see schema.py module docstring below)."""
    iana_name: str

    def current_utc_offset(self) -> str:
        """Computed on demand for display only - never stored, since offset shifts with DST."""
        offset = datetime.now(ZoneInfo(self.iana_name)).strftime("%z")
        return f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC+00:00"


@dataclass
class Kingdom:
    id: int
    name: str


@dataclass
class Alliance:
    id: int
    name: str
    kingdom_id: int
    discord_guild_id: str
    discord_guild_name: str


@dataclass
class Account:
    id: int
    account_type: AccountType
    account_name: str  # discord username for discord-users; admin-entered for manual-users
    time_zone: str  # IANA name, FK -> TimeZone.iana_name
    # Discord fields - populated for AccountType.DISCORD_USER, None for AccountType.MANUAL_USER
    discord_user_id: str | None = None
    discord_username: str | None = None
    discord_global_name: str | None = None
    discord_avatar_url: str | None = None
    is_super_admin: bool = False
    # Audit columns. create_account_id is None for self-registered (Discord OAuth) accounts;
    # it's set to the admin's account_id for manually-created accounts.
    create_account_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Player:
    id: int
    account_id: int
    alliance_id: int
    kingshot_id: str
    kingshot_name: str
    discord_nickname: str | None
    power: int
    town_center_level: int
    roles: list[Role] = field(default_factory=list)  # e.g. [Role.USER] or [Role.ADMIN]
    create_account_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TimeSlot:
    id: int
    player_id: int
    event_id: int
    local_start: time  # time-only (no date) - the player's recurring local availability window
    local_end: time
    time_slot_type: TimeSlotType = TimeSlotType.PREFERRED
    needs_review: bool = False
    create_account_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Event:
    id: int
    alliance_id: int
    name: str
    description: str
    begin_date: date | None = None  # date-only window during which the event may occur
    end_date: date | None = None
    qty_to_schedule: int = 1  # how many occurrences of this event to schedule within the window
    active_ind: bool = True
    scheduled_start: datetime | None = None  # the actual scheduled occurrence, once determined
    scheduled_end: datetime | None = None
    is_published: bool = False
    create_account_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
