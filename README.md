# Kingshot Event Scheduling - Mock UI

## Run it
```
uv sync
cp .env.example .env   # fill in real Discord app credentials
uv run python -m app.main
```
Run from the project root (not from inside `app/`) — the `-m app.main` form is
what makes the `app.*` imports resolve correctly.
Visit http://localhost:8080 — you'll land on /dashboard.

## What's real vs. mocked
- **Real**: Discord OAuth2 login (`/register`), bot-token guild verification
  (`auth/discord_guild.py`, used from the "Add Player" dialog).
- **Mocked**: all data lives in-memory (`models/sample_data.py`), resets on
  restart. Role-based access is previewed via the "Previewing as" picker in
  the header (top right) rather than real role assignment.

## Try the role gating
Use the account/role dropdowns in the header. `/admin` only appears (and is
only accessible) when previewing as **SuperAdmin**. Time slots and player
lists narrow to "your own" data unless you're previewing an elevated role.

## Project layout
```
kingshot_scheduler/          # repo root - pyproject.toml, uv.lock, README live here
└── app/                     # the actual Python package; deploy this whole folder as-is
    ├── main.py              # entry point, imports pages so their @ui.page routes register
    ├── pages/                # one file per functional area from web_app_requirements.md
    ├── components/           # shared header/nav (layout.py) + fake role switcher (role_switcher.py)
    ├── models/               # dataclasses (schema.py) + seeded fake data (sample_data.py)
    └── auth/                 # Discord OAuth login + bot-token guild membership check
```
All internal imports are `app.`-prefixed (e.g. `from app.models.schema import ...`),
so the app must always be run as a module from the repo root
(`uv run python -m app.main`), not by `cd`-ing into `app/` and running `main.py` directly.

## Known limitations of this mock
- No persistence (SQLite comes later)
- No real role assignment — only the preview switcher
- No scheduling algorithm
- Account/Alliance linkage is approximated through Player records, since the
  real data model doesn't directly connect Account -> Alliance
