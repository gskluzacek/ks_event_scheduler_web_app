from __future__ import annotations

from nicegui import ui

from app.components import layout, role_switcher
from app.data import accounts as accounts_repo
from app.data import alliances as alliances_repo
from app.data import players as players_repo
from app.data import time_slots as time_slots_repo
from app.models.schema import Player, Role
from app.utils.slot_times import format_end_24h


@ui.page("/search")
async def search_page() -> None:
    ui.page_title("Search - Kingshot Scheduler")
    async with layout.frame("/search"):
        ui.label("Search").classes("text-2xl font-bold")
        elevated = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN, Role.SCHEDULER_ADMIN)

        query = ui.input("Search accounts, players, or time slots…").props("outlined clearable").classes("w-full")
        results = ui.column().classes("w-full gap-4")

        async def run_search() -> None:
            results.clear()
            term = (query.value or "").lower().strip()
            all_players = await players_repo.list_players()
            alliance_name_by_id = {a.alliance_id: a.name for a in await alliances_repo.list_alliances()}
            with results:
                await _render_accounts(term, elevated)
                _render_players(all_players, alliance_name_by_id, term, elevated)
                await _render_slots(all_players, term)

        query.on_value_change(run_search)
        await run_search()


async def _render_accounts(term: str, elevated: bool) -> None:
    all_accounts = await accounts_repo.list_accounts()
    matches = [a for a in all_accounts if term in a.account_name.lower()] if term else all_accounts
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Accounts").classes("font-semibold")
        for a in matches:
            label = f"{a.account_name} — {a.time_zone}"
            if elevated:
                label += f"  (id: {a.account_id})"
            ui.label(label)


def _render_players(
    all_players: list[Player], alliance_name_by_id: dict[int, str], term: str, elevated: bool
) -> None:
    matches = [p for p in all_players if term in p.kingshot_name.lower() or term in p.kingshot_id.lower()] \
        if term else all_players
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Players").classes("font-semibold")
        for p in matches:
            alliance = alliance_name_by_id.get(p.alliance_id, "?")
            label = f"{p.kingshot_name} ({alliance}) — Power {p.power:,}"
            if elevated:
                label += f", TC {p.town_center_level}"
            ui.label(label)


async def _render_slots(all_players: list[Player], term: str) -> None:
    if not term:
        return
    matching_player_ids = [p.player_id for p in all_players if term in p.kingshot_name.lower()]
    matches = await time_slots_repo.list_time_slots(player_ids=matching_player_ids)
    if not matches:
        return
    with ui.card().classes("w-full"):
        ui.label("Time Slots").classes("font-semibold")
        for s in matches:
            ui.label(f"{s.start_time.strftime('%H:%M')} - {format_end_24h(s.end_time)} ({s.tslot_type.value})")
