"""
Entry point. Run from the project root with: uv run python -m app.main

Importing each `app.pages.*` module is what actually registers its
`@ui.page` routes (the decorator runs at import time) - main.py itself
stays thin. This mirrors the "Multi-Page App Pattern" in nicegui_llms.md.
"""
from __future__ import annotations

from nicegui import ui

from app.db import init_db
from app.pages import admin, auth, dashboard, events, players, search, timeslots

# NOTE: app.pages.accounts has no @ui.page route anymore - it's imported by
# players.py directly (account CRUD is surfaced from the Accounts & Players
# page's account cards, not a standalone page). No need to import it here too.


@ui.page("/")
def index() -> None:
    ui.navigate.to("/dashboard")


init_db()
auth.register_fastapi_routes()

ui.run(
    title="Kingshot Scheduler",
    storage_secret="dev-only-change-me",  # required for app.storage.user; move to .env before real use
    reload=True,
)
