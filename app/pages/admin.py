from __future__ import annotations

from nicegui import ui
from sqlalchemy.exc import IntegrityError

from app.components import layout, role_switcher
from app.data import alliances as alliances_repo
from app.data import kingdoms as kingdoms_repo
from app.data import time_zones as time_zones_repo
from app.models.schema import Kingdom, Role


@ui.page("/admin")
async def admin_page() -> None:
    ui.page_title("Site Maintenance - Kingshot Scheduler")
    async with layout.frame("/admin"):
        if not role_switcher.is_at_least(Role.SUPER_ADMIN):
            ui.label("SuperAdmin access required.").classes("text-negative text-lg")
            return

        ui.label("Site Maintenance").classes("text-2xl font-bold")

        with ui.tabs().classes("w-full") as tabs:
            kingdoms_tab = ui.tab("Kingdoms & Alliances")
            tz_tab = ui.tab("Time Zones")
        with ui.tab_panels(tabs, value=kingdoms_tab).classes("w-full"):
            with ui.tab_panel(kingdoms_tab):
                await kingdom_alliance_panel()
            with ui.tab_panel(tz_tab):
                await timezone_panel()


@ui.refreshable
async def kingdom_alliance_panel() -> None:
    kingdoms = await kingdoms_repo.list_kingdoms()
    alliances = await alliances_repo.list_alliances()
    ui.button("Add Kingdom", icon="add", on_click=_open_add_kingdom).props("outlined")
    for kingdom in kingdoms:
        with ui.card().classes("w-full"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(kingdom.name).classes("font-semibold")
                ui.button("Add Alliance", icon="add",
                           on_click=lambda k=kingdom: _open_add_alliance(k)).props("dense outlined")
            for alliance in [a for a in alliances if a.kingdom_id == kingdom.kingdom_id]:
                with ui.row().classes("items-center gap-4 pl-4"):
                    ui.icon("shield").classes("text-grey-6")
                    ui.label(alliance.name)
                    ui.label(f"guild: {alliance.discord_guild_name} ({alliance.discord_guild_id})") \
                        .classes("text-xs text-grey-5")


@ui.refreshable
async def timezone_panel() -> None:
    zones = await time_zones_repo.list_time_zones()
    ui.button("Add Time Zone", icon="add", on_click=_open_add_timezone).props("outlined")
    columns = [
        {"name": "region", "label": "Region", "field": "region", "sortable": True},
        {"name": "location", "label": "Location", "field": "location", "sortable": True},
        {"name": "utc_offset", "label": "Current UTC Offset", "field": "utc_offset"},
    ]
    # utc_offset is computed on the fly for display only - it is never stored (see schema.TimeZone).
    rows = [
        {"id": z.timezone_id, "region": z.region, "location": z.location, "utc_offset": z.current_utc_offset()}
        for z in zones
    ]
    ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")


def _open_add_timezone() -> None:
    with ui.dialog() as dialog, ui.card():
        ui.label("Add Time Zone").classes("font-bold")
        region = ui.input("Region (e.g. America)").props("outlined")
        location = ui.input("Location (e.g. Chicago)").props("outlined")

        async def submit() -> None:
            region_value, location_value = (region.value or "").strip(), (location.value or "").strip()
            if not (region_value and location_value):
                ui.notify("Region and location are required", type="warning")
                return
            try:
                await time_zones_repo.create_time_zone(region=region_value, location=location_value)
            except IntegrityError:
                ui.notify(f"{region_value}/{location_value} already exists.", type="warning")
                return
            dialog.close()
            timezone_panel.refresh()

        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")
    dialog.open()


def _open_add_kingdom() -> None:
    with ui.dialog() as dialog, ui.card():
        ui.label("Add Kingdom").classes("font-bold")
        name = ui.input("Kingdom Name").props("outlined")

        async def submit() -> None:
            if not (name.value and name.value.strip()):
                return
            try:
                await kingdoms_repo.create_kingdom(
                    name=name.value.strip(), create_account_id=role_switcher.current_account_id()
                )
            except IntegrityError:
                ui.notify(f"A kingdom named {name.value.strip()!r} already exists.", type="warning")
                return
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

        async def submit() -> None:
            if not (name.value and name.value.strip() and guild_id.value and guild_id.value.strip()):
                return
            try:
                await alliances_repo.create_alliance(
                    kingdom_id=kingdom.kingdom_id,
                    name=name.value.strip(),
                    discord_guild_id=guild_id.value.strip(),
                    discord_guild_name=(guild_name.value or "").strip() or name.value.strip(),
                    create_account_id=role_switcher.current_account_id(),
                )
            except IntegrityError as e:
                # The table's UNIQUE constraints are the source of truth (one guild per alliance,
                # alliance names unique within a kingdom); this just turns the failure into a message.
                if "discord_guild_id" in str(e.orig):
                    ui.notify("That Discord guild already belongs to another alliance.", type="warning")
                else:
                    ui.notify(f"{kingdom.name} already has an alliance named {name.value.strip()!r}.", type="warning")
                return
            dialog.close()
            kingdom_alliance_panel.refresh()

        with ui.row().classes("justify-end w-full gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")
    dialog.open()
