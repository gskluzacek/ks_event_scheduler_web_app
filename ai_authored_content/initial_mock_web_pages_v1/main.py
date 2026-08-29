"""
Entry point. Run with: uv run main.py

Importing each `pages.*` module is what actually registers its `@ui.page`
routes (the decorator runs at import time) - main.py itself stays thin.
This mirrors the "Multi-Page App Pattern" in nicegui_llms.md.
"""
from __future__ import annotations

from nicegui import ui

from pages import accounts, admin, auth, dashboard, events, players, search, timeslots


@ui.page("/")
def index() -> None:
    ui.navigate.to("/dashboard")


auth.register_fastapi_routes()

ui.run(
    title="Kingshot Scheduler",
    storage_secret="dev-only-change-me",  # required for app.storage.user; move to .env before real use
    reload=True,
)
