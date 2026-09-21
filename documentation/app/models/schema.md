# app/models/schema.py

## Purpose
Every table as a `SQLModel` class, plus the enums they use. Primary keys have descriptive names (`account_id`, not `id`).
Tables are created by `init_db()`; see [../db.md](../db.md) for the foreign-key PRAGMA and the no-migration caveat.

## Enums
- `Role` - `User`, `Admin`, `PowerAdmin`, `SchedulerAdmin`, `SuperAdmin`. SuperAdmin is account-level
  (`Account.is_super_admin`) and never appears in `player_role`.
- `AccountType` - `discord-user`, `manual-user`.
- `TimeSlotType` - `preferred`, `acceptable`, `avoid`.
- `TOWN_CENTER_LEVELS` - `"1"`-`"30"`, then `"TG1-1"` ... `"TG5-5"` (a string, not a number).
Enum columns store the enum's value (e.g. `manual-user`), guarded by a CHECK constraint built from the enum.

## Tables
| Table | Key columns and rules |
|---|---|
| `time_zone` | `timezone_id`, `region`, `location`; UNIQUE(region, location). The IANA name is `region/location`; UTC offsets are computed for display, never stored. |
| `kingdom` | `kingdom_id`, `name` (unique); audit columns. |
| `alliance` | `alliance_id`, `kingdom_id` (FK), `name`, `discord_guild_id` (UNIQUE: one guild per alliance), `discord_guild_name`; UNIQUE(kingdom_id, name); audit columns. |
| `account` | `account_id`, `account_type`, `account_name` (unique), `time_zone` (IANA name), Discord identity and OAuth token columns (Discord accounts only), `is_super_admin`; `discord_user_id` unique; audit columns. Tokens are plain text today and must be encrypted before going live. |
| `player` | `player_id`, `account_id` (FK), `alliance_id` (FK), `kingshot_id`, `kingshot_name`, `discord_nickname`, `power`, `town_center_level`, `discord_guild_avatar_url`; audit columns. |
| `player_role` | (`player_id` FK, `role`) composite key; CHECK excludes SuperAdmin. |
| `event` | `event_id`, `alliance_id` (FK), `event_name`, `event_desc`, `begin_date`/`end_date` (nullable window), `qty_to_schedule` (>= 1), `active_ind`, audit columns; UNIQUE(alliance_id, event_name); CHECK begin_date <= end_date. Temporary columns planned for removal: `scheduled_start`, `scheduled_end`, `is_published`. |
| `time_slot` | `tslot_id`, `event_id` (FK), `player_id` (FK), `tslot_type`, `priority` (nullable, 1 = highest, no UI yet), `start_time`, `end_time`, `confirmed_ind` (default True), audit columns; CHECK `end_time > start_time`. |

## Time slot conventions
- Times are time-of-day only (the player's local time). `end_time` is the picked end **minus one second**
  (picked 12:15 PM is stored `12:14:59`; a midnight end is `23:59:59`) so back-to-back slots never share an instant.
- `confirmed_ind` is True when the slot is confirmed. A SchedulerAdmin/SuperAdmin can set it False to ask the owning
  account to re-confirm; only the owner sets it back to True.
- One player may not have overlapping slots for the same event (any type). SQLite has no exclusion constraints, so this is
  enforced by two triggers (`trg_time_slot_no_overlap_insert` / `_update`) created with the table. A future PostgreSQL move
  should use an exclusion constraint.

## Audit columns
`create_account_id` (null when a user created their own row), `created_at`, `update_account_id`, `updated_at`; plain
integers with no foreign key.
