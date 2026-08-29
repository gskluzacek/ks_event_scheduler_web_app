# Kingshot Event Scheduling - Mock UI

## Run it
```
uv sync
cp .env.example .env   # fill in real Discord app credentials
uv run python main.py
```
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
- `main.py` — entry point, imports pages so their @ui.page routes register
- `pages/` — one file per functional area from web_app_requirements.md
- `components/` — shared header/nav (`layout.py`) and the fake role
  switcher (`role_switcher.py`)
- `models/` — dataclasses (`schema.py`) + seeded fake data (`sample_data.py`)
- `auth/` — Discord OAuth login + bot-token guild membership check

## Known limitations of this mock
- No persistence (SQLite comes later)
- No real role assignment — only the preview switcher
- No scheduling algorithm
- Account/Alliance linkage is approximated through Player records, since the
  real data model doesn't directly connect Account -> Alliance
