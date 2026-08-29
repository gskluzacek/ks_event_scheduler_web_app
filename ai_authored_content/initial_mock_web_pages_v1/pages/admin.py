from __future__ import annotations

from nicegui import ui

from components import layout, role_switcher
from models.sample_data import alliances, kingdoms, time_zones
from models.schema import Alliance, Kingdom, Role, next_id


@ui.page("/admin")
def admin_page() -> None:
    ui.page_title("Site Maintenance - Kingshot Scheduler")
    with layout.frame("/admin"):
        if not role_switcher.is_at_least(Role.SUPER_ADMIN):
            ui.label("SuperAdmin access required.").classes("text-negative text-lg")
            return

        ui.label("Site Maintenance").classes("text-2xl font-bold")

        with ui.tabs().classes("w-full") as tabs:
            kingdoms_tab = ui.tab("Kingdoms & Alliances")
            tz_tab = ui.tab("Time Zones")
        with ui.tab_panels(tabs, value=kingdoms_tab).classes("w-full"):
            with ui.tab_panel(kingdoms_tab):
                kingdom_alliance_panel()
            with ui.tab_panel(tz_tab):
                timezone_panel()


@ui.refreshable
def kingdom_alliance_panel() -> None:
    ui.button("Add Kingdom", icon="add", on_click=_open_add_kingdom).props("outlined")
    for kingdom in kingdoms:
        with ui.card().classes("w-full"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(kingdom.name).classes("font-semibold")
                ui.button("Add Alliance", icon="add",
                           on_click=lambda k=kingdom: _open_add_alliance(k)).props("dense outlined")
            for alliance in [a for a in alliances if a.kingdom_id == kingdom.id]:
                with ui.row().classes("items-center gap-4 pl-4"):
                    ui.icon("shield").classes("text-grey-6")
                    ui.label(alliance.name)
                    ui.label(f"guild: {alliance.discord_guild_name} ({alliance.discord_guild_id})") \
                        .classes("text-xs text-grey-5")


@ui.refreshable
def timezone_panel() -> None:
    columns = [
        {"name": "iana_name", "label": "IANA Name", "field": "iana_name", "sortable": True},
        {"name": "utc_offset", "label": "UTC Offset", "field": "utc_offset"},
    ]
    rows = [{"iana_name": tz.iana_name, "utc_offset": tz.utc_offset} for tz in time_zones]
    ui.table(columns=columns, rows=rows, row_key="iana_name").classes("w-full").props("flat bordered")


def _open_add_kingdom() -> None:
    with ui.dialog() as dialog, ui.card():
        ui.label("Add Kingdom").classes("font-bold")
        name = ui.input("Kingdom Name").props("outlined")

        def submit() -> None:
            if not name.value:
                return
            kingdoms.append(Kingdom(id=next_id(), name=name.value))
            dialog.close()
            kingdom_alliance_panel.refresh()

        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")
    dialog.open()


def _open_add_alliance(kingdom: Kingdom) -> None:
    with ui.dialog() as dialog, ui.card():
        ui.label(f"Add Alliance to {kingdom.name}").classes("font-bold")
        name = ui.input("Alliance Name").props("outlined")
        guild_id = ui.input("Discord Guild ID").props("outlined")
        guild_name = ui.input("Discord Guild Name").props("outlined")

        def submit() -> None:
            if not (name.value and guild_id.value):
                return
            alliances.append(Alliance(
                id=next_id(), name=name.value, kingdom_id=kingdom.id,
                discord_guild_id=guild_id.value, discord_guild_name=guild_name.value or name.value,
            ))
            dialog.close()
            kingdom_alliance_panel.refresh()

        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")
    dialog.open()
