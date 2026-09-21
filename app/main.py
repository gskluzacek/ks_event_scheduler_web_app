"""
Entry point. Run from the project root with: uv run python -m app.main

Importing each `app.pages.*` module is what actually registers its
`@ui.page` routes (the decorator runs at import time) - main.py itself
stays thin. This mirrors the "Multi-Page App Pattern" in nicegui_llms.md.
"""
from __future__ import annotations

from nicegui import app, ui

from app.db import init_db
from app.pages import admin, auth, dashboard, events, players, search, setup, timeslots
from app.setup_gate import SetupGateMiddleware
from app.utils.storage import clear_stored_user_sessions

# NOTE: app.pages.accounts has no @ui.page route anymore - it's imported by
# players.py directly (account CRUD is surfaced from the Accounts & Players
# page's account cards, not a standalone page). No need to import it here too.


@ui.page("/")
def index() -> None:
    ui.navigate.to("/dashboard")


if init_db():
    # A brand-new database (first run, or kingshot.db was deleted while testing): every browser's saved
    # session ids (preview account, filters) now point at rows that don't exist, so start them empty.
    # Only catches a DB created by this app start - one first created by a seed script is not
    # detected here; the get_valid_id()/safe_select() guards cover that case.
    clear_stored_user_sessions()
auth.register_fastapi_routes()
app.add_middleware(SetupGateMiddleware)

ui.run(
    title="Kingshot Scheduler",
    storage_secret="dev-only-change-me",  # required for app.storage.user; move to .env before real use
    reload=True,
)
