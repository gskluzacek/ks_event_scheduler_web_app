from __future__ import annotations

from nicegui import ui

from app.components import layout, role_switcher
from app.models.sample_data import accounts, events, players, time_slots


@ui.page("/dashboard")
async def dashboard_page() -> None:
    ui.page_title("Dashboard - Kingshot Scheduler")
    async with layout.frame("/dashboard"):
        role = role_switcher.current_role()
        ui.label(f"Welcome back — previewing as {role.value}").classes("text-2xl font-bold")

        with ui.row().classes("w-full gap-4"):
            _stat_card("Accounts", len(accounts), "badge")
            _stat_card("Players", len(players), "groups")
            _stat_card("Open Time Slots", len(time_slots), "schedule")
            _stat_card("Events", len(events), "event")

        with ui.card().classes("w-full"):
            ui.label("Upcoming Events").classes("text-lg font-semibold")
            for event in events:
                with ui.row().classes("items-center justify-between w-full py-1"):
                    ui.label(event.name)
                    ui.badge("Published" if event.is_published else "Draft",
                              color="positive" if event.is_published else "grey")


def _stat_card(label: str, value: int, icon: str) -> None:
    with ui.card().classes("flex-1 items-center"):
        ui.icon(icon, size="2rem").classes("text-primary")
        ui.label(str(value)).classes("text-3xl font-bold")
        ui.label(label).classes("text-grey-6")
