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
from datetime import datetime
from enum import Enum
from itertools import count

_id_counter = count(1)


def next_id() -> int:
    return next(_id_counter)


class Role(str, Enum):
    USER = "User"
    ADMIN = "Admin"
    POWER_ADMIN = "PowerAdmin"
    SCHEDULER_ADMIN = "SchedulerAdmin"
    SUPER_ADMIN = "SuperAdmin"  # account-level, not tied to an alliance


@dataclass
class TimeZone:
    iana_name: str
    utc_offset: str  # display string e.g. "UTC-05:00"; real offset varies with DST


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
    discord_user_id: str
    discord_username: str
    discord_avatar_url: str | None
    time_zone: str  # IANA name, FK -> TimeZone.iana_name
    is_super_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


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


@dataclass
class TimeSlot:
    id: int
    player_id: int
    event_id: int
    local_start: datetime
    local_end: datetime
    needs_review: bool = False


@dataclass
class Event:
    id: int
    alliance_id: int
    name: str
    description: str
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    is_published: bool = False
