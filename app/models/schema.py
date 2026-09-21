"""
Data model. Being migrated table-by-table from in-memory dataclasses to real
SQLite tables (see web_app_requirements.md > Data Model Overview) - see
app/db.py and app/data/ for the SQLModel/repository side of that migration.

TimeZone, Account, Player, PlayerRole, Kingdom, Alliance, Event and TimeSlot are real
`SQLModel` tables now. SampleEvent/SampleTimeSlot are the transitional in-memory
versions of Event/TimeSlot (module-level lists in app/models/sample_data.py), kept only
until their pages migrate; Module-level state is
normally an anti-pattern in NiceGUI (shared across all users - see
nicegui_llms.md Mental Model #2), but for this mock every "user" is really
just us previewing roles, so a shared in-memory store is fine and even
useful (edits by one role are visible when you switch roles).

Primary keys use descriptive names (`account_id`, not `id`) rather than the
NiceGUI/SQLModel default - decided 2026-09, applied table-by-table as each
migrates off `sample_data.py`. Migrated tables keep a read-only `.id`
property alias so not-yet-migrated page code keeps working unchanged; the
alias is deleted (and call sites fixed) when that page's own patch lands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from enum import Enum
from itertools import count

from dateutil import tz
from sqlalchemy import DDL, Enum as SAEnum, event as sa_event
from sqlmodel import CheckConstraint, Field, SQLModel, UniqueConstraint

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


# Town Center level, as a string rather than a plain int: past level 30 the game
# switches to a "TGx-y" naming scheme (tier x, sub-level y) rather than continuing
# to count up numerically, so this can't be represented as a simple integer range.
TOWN_CENTER_LEVELS: list[str] = [str(n) for n in range(1, 31)] + [
    f"TG{tier}-{level}" for tier in range(1, 6) for level in range(1, 6)
]


class TimeZone(SQLModel, table=True):
    """IANA name split into region + location (per web_app_requirements.md > time_zone),
    so the UI can offer two cascading dropdowns instead of one very long list!
    """
    __tablename__ = "time_zone"
    __table_args__ = (UniqueConstraint("region", "location", name="uq_time_zone_region_location"),)

    timezone_id: int | None = Field(default=None, primary_key=True)
    region: str      # e.g. "America" - the part before the "/"
    location: str    # e.g. "Chicago" - the part after the "/"

    @property
    def id(self) -> int | None:  # transitional alias - see module docstring
        return self.timezone_id

    @property
    def iana_name(self) -> str:
        return f"{self.region}/{self.location}"

    def current_utc_offset(self) -> str:
        """Computed on demand for display only - never stored, since offset shifts with DST."""
        local_tz = tz.gettz(self.iana_name)
        if local_tz is None:
            return "UTC+00:00"
        offset = datetime.now(timezone.utc).astimezone(local_tz).strftime("%z")
        return f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC+00:00"


class Kingdom(SQLModel, table=True):
    __tablename__ = "kingdom"
    __table_args__ = (UniqueConstraint("name", name="uq_kingdom_name"),)

    kingdom_id: int | None = Field(default=None, primary_key=True)
    name: str  # e.g. "#1542"
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Alliance(SQLModel, table=True):
    """Belongs to exactly one kingdom and has exactly one Discord guild (per
    web_app_requirements.md > relationships), hence the unique constraints below."""
    __tablename__ = "alliance"
    __table_args__ = (
        UniqueConstraint("kingdom_id", "name", name="uq_alliance_kingdom_id_name"),
        UniqueConstraint("discord_guild_id", name="uq_alliance_discord_guild_id"),
    )

    alliance_id: int | None = Field(default=None, primary_key=True)
    kingdom_id: int = Field(foreign_key="kingdom.kingdom_id", index=True)
    name: str
    discord_guild_id: str
    discord_guild_name: str
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Account(SQLModel, table=True):
    __tablename__ = "account"
    # NULLs don't collide under a unique constraint, so manual accounts
    # (discord_user_id always None) are unaffected by that one - it only stops
    # a second account from ever being created for the same real Discord
    # identity. account_name IS required to be globally unique, manual
    # accounts included - two accounts with the same display name would be
    # genuinely confusing (per Greg, 2026-09). The CHECK constraint is a
    # last line of defense against a bad account_type getting written by
    # something other than this app's own Account(...) + Pydantic validation
    # (e.g. a different tool editing the SQLite file directly) - kept in sync
    # with AccountType's actual values rather than hardcoded.
    __table_args__ = (
        UniqueConstraint("discord_user_id", name="uq_account_discord_user_id"),
        UniqueConstraint("account_name", name="uq_account_account_name"),
        CheckConstraint(
            "account_type IN (" + ", ".join(f"'{t.value}'" for t in AccountType) + ")",
            name="ck_account_account_type",
        ),
    )

    account_id: int | None = Field(default=None, primary_key=True)
    # Explicit sa_type: SQLAlchemy's default Enum column stores the member's
    # NAME ("MANUAL_USER"), not AccountType's own .value ("manual-user") - this
    # makes it store .value instead, which is what the CHECK constraint below
    # (and anything inspecting the raw SQLite file) expects.
    account_type: AccountType = Field(
        sa_type=SAEnum(AccountType, values_callable=lambda enum_cls: [e.value for e in enum_cls])
    )
    account_name: str  # discord username for discord-users; admin-entered for manual-users
    time_zone: str  # IANA name, FK -> TimeZone.iana_name
    # Discord fields - populated for AccountType.DISCORD_USER, None for AccountType.MANUAL_USER
    discord_user_id: str | None = None
    discord_username: str | None = None
    discord_global_name: str | None = None
    discord_avatar_url: str | None = None
    # OAuth tokens - populated at registration/login for DISCORD_USER accounts only.
    # Needed to support the "refresh from Discord" action (app/pages/accounts.py)
    # without asking the user to log in again every time. NOTE: plain columns are
    # fine while this is a solo-dev sandbox; encrypt at rest before real use.
    discord_access_token: str | None = None
    discord_refresh_token: str | None = None
    discord_token_expires_at: datetime | None = None
    is_super_admin: bool = False
    # Audit columns. create_account_id is None for self-registered (Discord OAuth) accounts;
    # it's set to the admin's account_id for manually-created accounts.
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Player(SQLModel, table=True):
    """A Kingshot player belonging to one account and one alliance. Roles live in
    the separate `player_role` table (PlayerRole below), not on this row - see
    app/data/players.py's roles_by_player_id()/set_roles().

    `alliance_id` is a real FK to `alliance` (enforced - see app/db.py's foreign_keys
    PRAGMA), so the preview players can only be seeded after the preview alliances.
    """
    __tablename__ = "player"

    player_id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.account_id", index=True)
    alliance_id: int = Field(foreign_key="alliance.alliance_id", index=True)
    kingshot_id: str
    kingshot_name: str
    discord_nickname: str | None = None
    power: int
    town_center_level: str  # one of TOWN_CENTER_LEVELS
    discord_guild_avatar_url: str | None = None  # guild-specific avatar override; None means "use the account's global avatar instead"
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlayerRole(SQLModel, table=True):
    """One row per (player, role). SuperAdmin is account-level (Account.is_super_admin),
    so it's deliberately excluded here - same reasoning as the CHECK below."""
    __tablename__ = "player_role"
    __table_args__ = (
        CheckConstraint(
            "role IN (" + ", ".join(f"'{r.value}'" for r in Role if r is not Role.SUPER_ADMIN) + ")",
            name="ck_player_role_role",
        ),
    )

    player_id: int = Field(foreign_key="player.player_id", primary_key=True)
    role: Role = Field(
        primary_key=True,
        sa_type=SAEnum(Role, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
    )


class Event(SQLModel, table=True):
    """An alliance event to be scheduled. `scheduled_start`, `scheduled_end` and
    `is_published` are TEMPORARY: they only exist so the migrated Events page keeps
    working as it did in memory; Greg plans to drop them (and their UI) once the
    migration is done. Dropping a column needs a fresh kingshot.db (no Alembic)."""
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint("alliance_id", "event_name", name="uq_event_alliance_id_event_name"),
        CheckConstraint("begin_date IS NULL OR end_date IS NULL OR begin_date <= end_date", name="ck_event_dates"),
        CheckConstraint("qty_to_schedule >= 1", name="ck_event_qty_to_schedule"),
    )

    event_id: int | None = Field(default=None, primary_key=True)
    alliance_id: int = Field(foreign_key="alliance.alliance_id", index=True)
    event_name: str
    event_desc: str = ""
    begin_date: date | None = None  # date-only window during which the event may occur
    end_date: date | None = None
    qty_to_schedule: int = 1  # how many occurrences of this event to schedule within the window
    active_ind: bool = True
    scheduled_start: datetime | None = None  # TEMPORARY - the actual scheduled occurrence, once determined
    scheduled_end: datetime | None = None  # TEMPORARY
    is_published: bool = False  # TEMPORARY
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TimeSlot(SQLModel, table=True):
    """A player's recurring local availability window (time only, no date) for an event.

    `end_time` is stored as the end the user picked MINUS ONE SECOND (picked 12:15 PM ->
    12:14:59; a midnight end -> 23:59:59), so back-to-back slots never share an instant and
    the no-overlap triggers below can use inclusive comparisons. The UI adds the second back
    for display. `confirmed_ind` is True when the slot is confirmed; a SchedulerAdmin/SuperAdmin
    sets it False to ask the owning account to re-confirm, and only the owner sets it back to True.
    """
    __tablename__ = "time_slot"
    __table_args__ = (
        CheckConstraint(
            "tslot_type IN (" + ", ".join(f"'{t.value}'" for t in TimeSlotType) + ")",
            name="ck_time_slot_tslot_type",
        ),
        CheckConstraint("priority IS NULL OR priority >= 1", name="ck_time_slot_priority"),
        CheckConstraint("end_time > start_time", name="ck_time_slot_end_after_start"),
    )

    tslot_id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    player_id: int = Field(foreign_key="player.player_id", index=True)
    tslot_type: TimeSlotType = Field(
        default=TimeSlotType.PREFERRED,
        sa_type=SAEnum(TimeSlotType, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
    )
    priority: int | None = None  # NULL = no priority; 1 = highest, larger = lower. No UI yet.
    start_time: time
    end_time: time
    confirmed_ind: bool = True
    create_account_id: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    update_account_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# One player may not have overlapping slots for the same event (any tslot_type). SQLite has no
# exclusion constraints, so this is a pair of triggers, installed whenever create_all() creates the
# table - which keeps the rule true even if some other tool edits the SQLite file. SQLite stores
# Time as 'HH:MM:SS.ffffff' text, so string comparison orders correctly. Both raise IntegrityError
# ("time_slot overlaps ..."). NOTE for a future PostgreSQL move: use an exclusion constraint instead.
_OVERLAP_MESSAGE = "time_slot overlaps an existing slot for this player and event"
for _trigger_name, _trigger_event, _own_row_filter in (
    ("trg_time_slot_no_overlap_insert", "INSERT", ""),
    ("trg_time_slot_no_overlap_update",
     "UPDATE OF player_id, event_id, start_time, end_time", " AND tslot_id <> NEW.tslot_id"),
):
    sa_event.listen(
        TimeSlot.__table__,
        "after_create",
        DDL(
            f"CREATE TRIGGER {_trigger_name} BEFORE {_trigger_event} ON time_slot "
            "WHEN EXISTS (SELECT 1 FROM time_slot WHERE player_id = NEW.player_id AND event_id = NEW.event_id "
            f"AND start_time <= NEW.end_time AND end_time >= NEW.start_time{_own_row_filter}) "
            f"BEGIN SELECT RAISE(ABORT, '{_OVERLAP_MESSAGE}'); END"
        ).execute_if(dialect="sqlite"),
    )


# Transitional in-memory versions, deleted along with sample_data's events/time_slots once the
# last page reading those lists has migrated.
@dataclass
class SampleTimeSlot:
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
class SampleEvent:
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
