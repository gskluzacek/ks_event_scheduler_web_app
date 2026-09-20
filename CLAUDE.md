# CLAUDE.md

Kingshot Scheduler (`kingshot-scheduler`): a Python/NiceGUI web app for planning and scheduling Kingshot alliance
events. Users register accounts (via Discord OAuth), manage players, record time-slot availability, and admins
coordinate event windows.

- Canonical repo: https://github.com/gskluzacek/ks_event_scheduler_web_app (this working directory is a checkout of it;
  the local folder is named `nice_gui_pocs`). Work on the latest `main`; pull before starting a feature.
- Owner: Greg Skluzacek, an experienced Python dev who was new to NiceGUI at project start. Through 2026-09-19 the code
  was built in the Claude desktop app project `ks_scheduler_web`, where Claude produced `git apply` patches that Greg applied,
  tested, and pushed. That project's instructions, memories and 19 chats were exported on 2026-09-20 to
  `ai_authored_content/desktop_claude_data_export/` (zips, git-ignored). The desktop project's only instruction was
  "clone the repo and pull latest main before coding a feature"; that doesn't apply in Claude Code, where this checkout is
  the repo. The most relevant chat is "Migrating from in-memory data to SQLite" (2026-09-16), plus "Phase 4 player table
  migration" (2026-09-19).

## Commands

```bash
uv sync                                        # install deps (Python >=3.14, see .python-version)
cp .env.example .env                           # then fill in Discord creds + STORAGE_SECRET
uv run python -m app.main                      # run the app -> http://localhost:8080
uv run python -m scripts.seed_preview_accounts # seed the 5 preview accounts (ids 1001-1005)
uv run python -m scripts.seed_preview_players  # seed preview players (needs accounts first)
```

Always run from the repo root with `-m`. All imports are `app.`-prefixed, so `cd app && python main.py` breaks.
There is no test suite and no CI yet; verification is manual (run the app, switch roles, click through pages).

## Backend migration status (in-memory -> SQLite) - READ THIS FIRST

The app began as an all-in-memory mock (`app/models/sample_data.py`) and is being migrated one table at a time to
SQLite via SQLModel. The DB file is `kingshot.db` at the repo root (git-ignored, created by `init_db()` on startup).

| Phase | Table(s) | State |
|---|---|---|
| 1-2 | `time_zone`, `account` groundwork + first-run setup wizard (`/setup`) | done |
| 3 | `account` | done |
| 4 | `player`, `player_role` | done (latest commits) |
| next | `kingdom`, `alliance`, `time_slot`, `event` | **still in-memory dataclasses** in `app/models/schema.py` + lists in `app/models/sample_data.py` |

Consequences to keep in mind:
- `player.alliance_id` has no DB foreign key yet (Alliance is in-memory, ids pinned to literals 2001-2006). Add
  `foreign_key="alliance.alliance_id"` when Alliance migrates, along with Kingdom.
- Time slots are in memory, so `delete_player()` can't cascade to them (orphans). Resolves when `time_slot` migrates.
- Pages still importing `sample_data`: dashboard, events, search, timeslots, players (for alliances/time slots),
  admin. Don't assume a page is DB-backed without checking.
- Migrated tables use descriptive PKs (`account_id`, `player_id`, `timezone_id`), not `id`. They keep a read-only `.id`
  property alias so unmigrated page code still works; delete the alias and fix call sites when that page migrates.
- Cleanup owed after migration: the "stale id" handling in `app/utils/storage.py` (`get_valid_id`) exists only because
  sample-data ids were renumbered on restart; remove it once everything is DB-backed.
- Before going live: `Account.discord_access_token` / `discord_refresh_token` are stored as plain text and must be
  encrypted at rest.

### Data-layer conventions (follow these when migrating the next table)
- Model: `SQLModel, table=True` class in `app/models/schema.py`, with `__tablename__`, descriptive PK, audit columns
  (`create_account_id`, `created_at`, `update_account_id`, `updated_at`).
- Enums are stored by `.value` via `SAEnum(..., values_callable=...)` and guarded by a `CheckConstraint` built from the
  enum, so the DB and the enum can't drift.
- Repository: one module per table in `app/data/` with sync `_private` functions using `get_session()` and public
  `async` wrappers using `nicegui.run.io_bound`. The SQLite driver is synchronous and would otherwise block NiceGUI's
  single event loop. Pages never touch `Session` directly. No in-memory mirror/cache.
- Update functions take `update_account_id` and stamp `updated_at`; callers pass `role_switcher.current_account_id()`.
- Seed data lives in `scripts/*.yaml` with fixed ids, loaded by idempotent `scripts/seed_*.py` (skip rows that exist).
- `init_db()` uses `create_all`, which does NOT alter existing tables. There is no migration tool (no Alembic), so a
  schema change to an existing table means deleting `kingshot.db` and re-running setup + seeds. Say so when you make one.

### Migration decisions Greg has already made (don't re-litigate)
- **Incremental, one page/table per change**, retiring the matching `sample_data` list as each lands. Pages that depend
  on not-yet-migrated tables are allowed to be temporarily disconnected from the DB rather than adding shims.
- **No in-memory mirror or write-through cache of DB tables.** Proposed once and explicitly rejected: each page queries
  exactly what it needs, and any in-memory list is just the ephemeral result of that query (must scale to a big DB).
- **Descriptive PK names** everywhere: `kingdom_id`, `alliance_id`, `event_id`, `player_id`, `account_id`, `timezone_id`.
- **Constraints belong in the DB, not just the app:** `account_name` is globally unique (manual accounts included),
  `discord_user_id` is unique (NULLs for manual accounts don't collide), `time_zone(region, location)` is unique, and enum
  columns get CHECK constraints. Rationale: other tools may edit the SQLite file, so don't assume only this app writes it.
- **Enum columns store the enum `.value`** (`"manual-user"`), not the member name; SQLAlchemy's default stores the name.
- **`player.alliance_id` is a plain int with pinned ids** until Alliance migrates (see above). `player_role` is its own table
  (matches `web_app_requirements.md`); SuperAdmin is never in it.
- **Planned `time_slot` schema** (agreed in chat, not yet built): `tslot_id`, `event_id`, `player_id`, `tslot_type`,
  `priority` (small int, NULL default = no priority, 1 = highest), `start_time`, `end_time`, `validate_ind` (pure rename of
  `needs_review`, same polarity, defaults False), plus the four audit columns. Current dataclass still uses the old names.
- **SQLite now, PostgreSQL possibly later** (per requirements), which is why SQLModel/SQLAlchemy and no raw SQLite-only SQL.
- **Idea under discussion, not decided:** removing `role_switcher.py` in favor of real login/logout via Discord OAuth
  (look up account by `discord_user_id`, store `account_id` in `app.storage.user`; role derived from
  `Account.is_super_admin` + the account's players' roles), possibly with an `ENABLE_ROLE_SWITCHER` env flag for dev.
  Don't start this without Greg's go-ahead.

### Preview data and fresh-DB recipe
Pinned ids matter because unmigrated data references them: preview accounts 1001-1005, alliances 2001-2006 (in
`sample_data.py`), players 3001-3012 (`scripts/preview_players.yaml`), and the in-memory time slots reference player ids
through named constants in `sample_data.py`. On a fresh DB: run the app, complete `/setup`, then
`seed_preview_accounts`, then `seed_preview_players`. Otherwise time slots point at players that don't exist.

## Architecture

```
app/
  main.py            entry point; init_db(), registers routes, adds SetupGateMiddleware, ui.run(reload=True)
  db.py              engine, init_db(), get_session()
  setup_gate.py      middleware: redirects gated routes to /setup until an account exists
  models/schema.py   Role/AccountType/TimeSlotType enums, SQLModel tables, remaining dataclasses
  models/sample_data.py  seeded in-memory data for not-yet-migrated tables
  data/              repositories (accounts, players, time_zones)
  pages/             one module per @ui.page (importing the module registers the route)
  components/        layout.py (header/nav, `async with layout.frame(route)`), role_switcher.py, timezone_select.py
  auth/              Discord OAuth2 (discord_oauth.py) + bot-token guild membership check (discord_guild.py)
  utils/             filters.py (persisted table filters), rate_limit.py, storage.py
scripts/             preview-data seeders + yaml
documentation/       requirements, todos, NiceGUI reference (see caveat below)
```

Routes: `/dashboard`, `/players` (Accounts & Players; account CRUD lives here, `pages/accounts.py` has no route of its
own), `/timeslots`, `/events`, `/search`, `/admin` (SuperAdmin only), `/setup` (first-run wizard), plus Discord auth
routes registered by `auth.register_fastapi_routes()`.

### Roles and access
Roles: User, Admin, PowerAdmin, SchedulerAdmin (per-player, table `player_role`) and SuperAdmin (account-level,
`Account.is_super_admin`, deliberately not in `player_role`). Roles are previewed with the "Previewing as" account/role
pickers in the header (`components/role_switcher.py`), not real login sessions yet. Real role-gating is enforced only in
the UI. A todo notes that server-side permission checks are needed for every data-modifying action.
Per-role, per-page capabilities are being documented in `documentation/screen_role_acctions.xlsx` (work in progress).

### Setup wizard
First run: `SetupGateMiddleware` sends `/`, `/dashboard`, etc. to `/setup` until an account exists. Steps: (1) upload
time-zone CSV (`assets/timezone_regions_locations.csv`), (2) create the SuperAdmin through the normal Discord OAuth flow,
landing back in the wizard, (3) kingdoms/alliances (stub). Pending Discord identity is only trusted right after the OAuth
redirect (`?authorized=1`).

## UI and permission decisions (from the desktop-app chats, Aug-Sep 2026)
Greg's stated intent as of 2026-09-20. The code is the source of truth where they differ.

**These decisions are under review.** Greg is reconsidering them while drafting `documentation/screen_role_acctions.xlsx`,
which will define, per role and per screen, what may be viewed and what actions are allowed on each displayed entity. He also
plans to revamp the filters. That matrix will supersede the role/visibility, filter and page-layout rules below. It is
deliberately on hold until the SQLite backend migration is finished, so **finish the migration first and don't redesign
permissions or filters in the meantime**; migrate pages with their current behavior.

**Who sees/does what**
- PowerAdmin = Admin + the ability to assign roles. Neither gets extra visibility on the Time Slots page (same as a User).
- Accounts & Players page: User and SchedulerAdmin see only their own account and its players. Admin/PowerAdmin see all
  accounts, can view but not edit them, can add players only for alliances they belong to, and see only players in those
  alliances. SuperAdmin sees all, edits accounts, and can add players for any alliance.
- Time Slots page: User/Admin/PowerAdmin see only their own account's players' slots. SchedulerAdmin sees slots for players in
  the alliances their account's players belong to. SuperAdmin sees everything. Filter order: Kingdom, Alliance (SuperAdmin
  only), Account (SchedulerAdmin and SuperAdmin), Player, Event, Needs Review.
- Roles editing: SuperAdmin can set `is_super_admin` on other accounts (not their own). SuperAdmin or PowerAdmin can edit a
  player's roles, but a PowerAdmin cannot edit their own roles. Valid role sets: none; Admin; PowerAdmin; SchedulerAdmin;
  Admin+SchedulerAdmin; PowerAdmin+SchedulerAdmin (never Admin+PowerAdmin). Use one consistent control for role selection,
  validate on save rather than dynamically disabling options.
- Accounts have no alliance of their own; alliance comes from their players, so an account with players in two alliances is
  visible/editable per each alliance's admins by design.

**Page layouts**
- Accounts & Players is one page (the standalone Accounts page was merged in on 2026-09-13). It is accounts-first: one card
  per account with View/Edit (and Add Player for admins), expandable child cards for players, several open at once.
  Records-per-page control (5/10/20/50, persisted in `app.storage.user`) instead of scroll-all, because NiceGUI renders real
  DOM nodes per card. Zero-player accounts show a disabled expander with a tooltip; an empty page shows "No data available".
  Filter order: Kingdom, Alliance, Account (admins only), Kingshot name. Kingdom/Alliance filters exclude zero-player accounts.
- Filters: dropdown options come only from the user's actual data and cascade from the cross-filtered result set, with fixed
  widths so they don't jump; options stay stable while typing in a text search. Filter and sort state persists per browser in
  `app.storage.user` (true per-tab isolation with `app.storage.tab` was deliberately deferred). After adding a player, refresh
  the filter row as well as the list.
- Time Slots is a `ui.table` with multi-select, and a toolbar strip holding Add/View/Edit (View/Edit enabled only when exactly
  one row is selected; multi-select is there for future bulk actions such as delete). Hour dropdown 12am-11pm, minute dropdown
  00/15/30/45, and both Add and Edit validate end > start (no overnight slots).
- Site-wide: light blue-gray tint (`#dbe4ee`) on table headers; time stamps shown in the viewing user's time zone.

**Dialog conventions**
- View shows every field, with `create_account_id`/`update_account_id` resolved to account names (a NULL create id means
  self-registered, so show the account's own name). Edit = the View content plus a separate editable section. Long Discord
  avatar URLs are truncated with a copy icon and a tooltip of the full value.
- Manual accounts: generic person icon, editable account name, no Discord refresh. Discord accounts: account name read-only,
  "refresh from Discord" pulls new values into the open dialog (the dialog stays open and the user must click Save). Refresh is
  rate limited to 10 per 4 hours, counted per acting account and per target account in `app.storage.user` (`utils/rate_limit.py`).
  Player edit: Kingshot name, power and town-center level editable; Discord nickname/guild avatar only via "Sync from Discord".
- Add Player: pick Kingdom, then Alliance (narrowed to that kingdom), then "Verify Guild Membership" (disabled until both are
  chosen); "Add Player" stays disabled until verification succeeds. Manual accounts skip verification. Guild membership is checked
  only here, not at registration.
- Avatars: global avatar on `Account`, guild avatar on `Player`, built from Discord hashes as full CDN URLs with `?size=2048`
  (CSS scales down). Display fallback: guild avatar, then global avatar, then generic icon. A todo proposes storing the pieces
  and building URLs in the UI instead.
- Town center level is a string: "1"-"30", then "TG1-1" through "TG5-5" (`TOWN_CENTER_LEVELS`).
- Times: store naive local datetimes plus the account's IANA zone name (region + location, chosen with two cascading
  dropdowns) and convert with `dateutil.tz.gettz`; never store UTC offsets.
- Project layout is the `app/` package with `app.`-prefixed imports (chosen over a flat layout); Python 3.14.

## NiceGUI rules of thumb for this repo
- Page handlers are `async`; anything hitting the DB goes through the `app/data` async wrappers.
- Module-level state is shared across all users. It's tolerated only for the remaining mock data.
- `app.storage.user` is per-browser and persists to disk; `app.storage.tab` for per-tab filter state;
  `app.storage.client` for per-connection data (used by role_switcher to hold the account list so sync helpers like
  `current_account_id()` keep working). contextvars do NOT propagate into NiceGUI event handler tasks.
- Use `layout.frame()` for every real page; it loads the accounts the role switcher depends on.
- Gotchas learned the hard way: `@ui.refreshable` containers delete elements inside them on refresh, including open
  dialogs, so give a dialog's detail view its own local refreshable and refresh the outer list on dialog close.
  `app.storage.tab` needs the websocket connection, which isn't available during synchronous page-function execution
  (await the client connection first). `ui.date` has no `label` parameter. Use `httpx.AsyncClient`, not `requests`.
  Stale values in `app.storage.user` survive DB wipes (persisted cookie plus `.nicegui/storage-*.json`); delete those
  files or use an incognito window when testing first-run flows.
- Page filter pattern: fetch the visible rows once per render, then narrow with pure helpers (`_narrow`,
  `_players_matching`, `_structured_filters`); cascading filters are reconciled from the cross-filtered result set.
- **`documentation/nicegui_llms.md` is the NiceGUI reference written for LLMs/AI coding assistants** (~1,400 lines:
  mental models, the Python-first rule, styling API, layout/input/display elements, tables/AG Grid/tree, async,
  storage, multi-page pattern). Consult it before writing or changing NiceGUI code and prefer its patterns over guessing
  from memory of the NiceGUI API. It's the source of the "Mental Model #N" references in code comments. Read the
  relevant section rather than the whole file.

## Config and secrets
`.env` (git-ignored) needs `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_BOT_TOKEN`, `DISCORD_REDIRECT_URI`,
`STORAGE_SECRET`. Never commit real secrets. Known wart: `app/main.py` hardcodes `storage_secret="dev-only-change-me"`
instead of reading `STORAGE_SECRET`; fix before real use. Keep OAuth `state` validation intact (CSRF), and surface
Discord/network failures to the user instead of swallowing them.

## Stale or non-runtime material - don't trust or edit without asking
- `documentation/app/**` (per-module markdown) is OUT OF DATE and predates the SQLite migration. Code and this file win.
  It also has no docs for `db.py`, `data/`, `setup.py`, `setup_gate.py`, `account_player.py`.
- `README.md` still says "all data lives in-memory" and "No persistence"; that is no longer true for accounts, players and
  time zones.
- `.github/copilot-instructions.md` and `.github/instructions/*` (plus `.github/agents/*`) are GitHub Copilot config.
  They pre-date the migration and omit SQLModel; treat as background only.
- `discord_integration_poc/`, `nicegui_exploration/`: historical/sandbox, not part of the runtime.
- `ai_authored_content/` (git-ignored, so absent from a fresh clone): the patches Claude desktop authored for Greg,
  which he applied to the repo. Not runtime code. It's the best record of *how* and *why* the code got this way:
  - `migrate_to_db/` holds every patch applied for the SQLite backend migration: `00_initial_sqlmodel_and_schema/`,
    `01_set_up_wizard/`, `02_migrate_time_zone_and_account/`, then numbered phase 4 (player table) patches
    `001-01` ... `005-01` (player table, players page, search/dashboard, timeslots, cleanup). Read these when you need
    the intent behind a migration step, and follow the same pattern for the next table.
  - `initial_mock_web_pages_v1a/` and `applied_patches/` are the earlier in-memory mock UI patches.
  - Treat as read-only history; the repo's current code is the source of truth, since later edits may differ.
- `documentation/todos.md` is an older backlog; `documentation/todos_2026_09_11.md` is the current one. Requirements are
  in `documentation/web_app_requirements.md`.

## Working agreements
- Greg wants to weigh alternatives and approve a plan before code is written for non-trivial changes: raise design forks
  and open questions first (as in the migration chats), then implement once decided. Trivial fixes don't need this.
- Greg works incrementally and tests each change by hand (e.g. delete `kingshot.db`, restart, walk the wizard), so keep
  changes small and say what to click to verify. Mention when a change requires deleting `kingshot.db`.
- Known follow-ups he has accepted as later work: alliance-scope the Search page (requirements say results should be
  alliance-scoped; it currently shows every role all players), server-side permission checks on writes, and the `rate_limit`
  on the Players page refresh not behaving (see `documentation/todos_2026_09_11.md`).
- Commit messages in this repo are short and phase-labelled (e.g. "phase 4 backend migration to sqlite - player table").
- Don't commit `kingshot.db` or `.env`.
- Match the surrounding code's comment style: comments here explain *why* (design decisions, gotchas), often with dates.
