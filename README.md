# Kingshot Event Scheduler

A NiceGUI web app for planning and scheduling Kingshot alliance events. Players register with Discord, add their Kingshot players,
and record the time windows they are available for each event; alliance admins use that to pick good event times.

Repository: https://github.com/gskluzacek/ks_event_scheduler_web_app

## Run it
Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).
```
uv sync
cp .env.example .env   # fill in the Discord app credentials and STORAGE_SECRET
uv run python -m app.main
```
Run from the repository root with `-m` (every import is `app.`-prefixed). Then open http://localhost:8080.

### First run
The database is `kingshot.db` (SQLite, git-ignored), created automatically. Until the first account exists, every page redirects to
the `/setup` wizard:
1. upload a time zone CSV (`assets/timezone_regions_locations.csv` works),
2. sign in with Discord to create the SuperAdmin account and choose its time zone,
3. (kingdoms and alliances are added afterwards from **Site Maintenance**).

### Preview data (optional, for development)
After setup, load sample accounts, kingdoms/alliances, players, events and time slots - **in this order**, from the repository root:
```
uv run python -m scripts.seed_preview_accounts
uv run python -m scripts.seed_preview_kingdoms_alliances
uv run python -m scripts.seed_preview_players
uv run python -m scripts.seed_preview_events_time_slots
```
Each script is safe to run twice. To start over, stop the app, delete `kingshot.db`, and start it again (a new database also clears
the browsers' saved session state). There is no migration tool: changing an existing table means recreating the database.

## What is real and what is a preview
- **Real:** all data lives in SQLite with enforced foreign keys and constraints; Discord OAuth2 sign-in for registration; the
  bot-token check that a user is a member of an alliance's Discord guild (when adding a player).
- **Preview only:** the "Previewing as" account and role dropdown in the header stands in for real login and role assignment (a
  development aid that will be replaced), and roles are not enforced on the server yet. The scheduling algorithm is not built.

## Tests
```
uv run pytest
```
Each test gets its own freshly seeded temporary database, so tests never touch `kingshot.db` or `.nicegui/`, need no network, and
can run in any order. See [tests/README.md](tests/README.md).

## Project layout
```
app/
  main.py            entry point (routes, middleware, first-run handling)
  db.py              SQLite engine, foreign-key PRAGMA, sessions
  setup_gate.py      redirects to /setup until the first account exists
  models/schema.py   every table (SQLModel) and enum
  data/              one repository module per table (async wrappers over sync queries)
  pages/             one module per page, plus shared account/player helpers
  components/        header/nav, the preview role switcher, safe_select, time zone picker
  auth/              Discord OAuth2 and guild-membership verification
  utils/             persisted filters, stale-id handling, rate limiting, slot time conversions
scripts/             preview-data seed scripts and their YAML files
tests/               pytest suite
documentation/       requirements, per-module docs (documentation/app/), todos, NiceGUI reference
assets/              time zone CSV and images
```
Start with `documentation/app/index.md` for a per-module tour and `documentation/web_app_requirements.md` for the requirements
and data model. `CLAUDE.md` has working notes for AI assistants (migration history, conventions, decisions).

## Known limitations
- `app/main.py` hardcodes the session storage secret (`dev-only-change-me`) instead of reading `STORAGE_SECRET`.
- Discord OAuth tokens are stored unencrypted in the account table.
- Role rules are enforced only in the UI, and Search is not alliance-scoped yet.
- The per-role, per-screen permission matrix and the filter behavior are being redesigned (`documentation/screen_role_acctions.xlsx`).
