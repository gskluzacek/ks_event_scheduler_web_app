from __future__ import annotations

from nicegui import ui

from components import layout, role_switcher
from models.sample_data import accounts, alliances, players, time_slots
from models.schema import Role


@ui.page("/search")
def search_page() -> None:
    ui.page_title("Search - Kingshot Scheduler")
    with layout.frame("/search"):
        ui.label("Search").classes("text-2xl font-bold")
        elevated = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN, Role.SCHEDULER_ADMIN)

        query = ui.input("Search accounts, players, or time slots…").props("outlined clearable").classes("w-full")
        results = ui.column().classes("w-full gap-4")

        def run_search() -> None:
            results.clear()
            term = (query.value or "").lower().strip()
            with results:
                _render_accounts(term, elevated)
                _render_players(term, elevated)
                _render_slots(term)

        query.on_value_change(run_search)
        run_search()


def _render_accounts(term: str, elevated: bool) -> None:
    matches = [a for a in accounts if term in a.discord_username.lower()] if term else accounts
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Accounts").classes("font-semibold")
        for a in matches:
            label = f"{a.discord_username} — {a.time_zone}"
            if elevated:
                label += f"  (id: {a.id})"
            ui.label(label)


def _render_players(term: str, elevated: bool) -> None:
    matches = [p for p in players if term in p.kingshot_name.lower() or term in p.kingshot_id.lower()] \
        if term else players
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Players").classes("font-semibold")
        for p in matches:
            alliance = next((a.name for a in alliances if a.id == p.alliance_id), "?")
            label = f"{p.kingshot_name} ({alliance}) — Power {p.power:,}"
            if elevated:
                label += f", TC {p.town_center_level}"
            ui.label(label)


def _render_slots(term: str) -> None:
    if not term:
        return
    matches = [s for p in players if term in p.kingshot_name.lower() for s in time_slots if s.player_id == p.id]
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Time Slots").classes("font-semibold")
        for s in matches:
            ui.label(f"{s.local_start.strftime('%Y-%m-%d %H:%M')} - {s.local_end.strftime('%H:%M')}")
