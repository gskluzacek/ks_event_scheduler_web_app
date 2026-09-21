# app Directory Documentation Index

This index links to documentation for every Python file under `app/`. It describes the code as of the SQLite
migration being finished (all data is in `kingshot.db`; nothing is held in memory any more). If a doc and the code
disagree, the code wins.

## Root Files
- [__init__.md](__init__.md)
- [main.md](main.md) - entry point
- [db.md](db.md) - SQLite engine, foreign-key PRAGMA, sessions
- [setup_gate.md](setup_gate.md) - first-run redirect middleware

## Subdirectories
- [auth/index.md](auth/index.md) - Discord OAuth2 and guild-membership check
- [components/index.md](components/index.md) - shared header/nav, preview role switcher, selects
- [data/index.md](data/index.md) - one repository module per table
- [models/index.md](models/index.md) - SQLModel tables
- [pages/index.md](pages/index.md) - one module per page (and shared page helpers)
- [utils/index.md](utils/index.md) - persisted filters, stale-id handling, rate limiting, slot time conversions

## Route to Module Cross-Reference
| Route | Page Documentation | Primary Dependencies |
|---|---|---|
| `/` | [main.md](main.md) | redirects to `/dashboard` |
| `/setup` | [pages/setup.md](pages/setup.md) | [pages/auth.md](pages/auth.md), [data/time_zones.md](data/time_zones.md), [data/accounts.md](data/accounts.md), [setup_gate.md](setup_gate.md) |
| `/register`, `/register/complete`, `/auth/discord/callback` | [pages/auth.md](pages/auth.md) | [auth/discord_oauth.md](auth/discord_oauth.md), [data/accounts.md](data/accounts.md) |
| `/dashboard` | [pages/dashboard.md](pages/dashboard.md) | [components/layout.md](components/layout.md), [data/accounts.md](data/accounts.md), [data/players.md](data/players.md), [data/events.md](data/events.md), [data/time_slots.md](data/time_slots.md) |
| `/players` (Accounts & Players) | [pages/players.md](pages/players.md) | [pages/account_player.md](pages/account_player.md), [pages/accounts.md](pages/accounts.md), [auth/discord_guild.md](auth/discord_guild.md), [components/safe_select.md](components/safe_select.md), [utils/filters.md](utils/filters.md), [data/players.md](data/players.md), [data/alliances.md](data/alliances.md), [data/kingdoms.md](data/kingdoms.md) |
| `/timeslots` | [pages/timeslots.md](pages/timeslots.md) | [data/time_slots.md](data/time_slots.md), [data/events.md](data/events.md), [utils/slot_times.md](utils/slot_times.md), [utils/filters.md](utils/filters.md), [components/safe_select.md](components/safe_select.md) |
| `/events` | [pages/events.md](pages/events.md) | [data/events.md](data/events.md), [data/alliances.md](data/alliances.md) |
| `/search` | [pages/search.md](pages/search.md) | [data/accounts.md](data/accounts.md), [data/players.md](data/players.md), [data/time_slots.md](data/time_slots.md) |
| `/admin` (SuperAdmin) | [pages/admin.md](pages/admin.md) | [data/kingdoms.md](data/kingdoms.md), [data/alliances.md](data/alliances.md), [data/time_zones.md](data/time_zones.md) |

There is no standalone `/accounts` page any more: account view/add/edit dialogs are launched from the account cards on
`/players` (see [pages/accounts.md](pages/accounts.md)).

## Related
- Data model and rules: [models/schema.md](models/schema.md), and `documentation/web_app_requirements.md`.
- Preview data: the `scripts/` folder (see the repository README).
- Tests: the `tests/` folder (see the repository README).
