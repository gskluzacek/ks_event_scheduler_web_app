from __future__ import annotations

from datetime import datetime, timedelta

from nicegui import ui

from components import layout, role_switcher
from models.sample_data import events, players, time_slots
from models.schema import Role, TimeSlot, next_id


def _visible_slots() -> list[TimeSlot]:
    if role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN):
        return time_slots
    my_player_ids = {p.id for p in players if p.account_id == role_switcher.current_account_id()}
    return [s for s in time_slots if s.player_id in my_player_ids]


@ui.page("/timeslots")
def timeslots_page() -> None:
    ui.page_title("Time Slots - Kingshot Scheduler")
    with layout.frame("/timeslots"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Time Slot Management").classes("text-2xl font-bold")
            ui.button("Add Time Slot", icon="add", on_click=_open_add_dialog).props("unelevated color=primary")
        slot_table()


@ui.refreshable
def slot_table() -> None:
    is_scheduler = role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN)
    rows = []
    for s in _visible_slots():
        player = next((p for p in players if p.id == s.player_id), None)
        event = next((e for e in events if e.id == s.event_id), None)
        rows.append({
            "id": s.id,
            "player": player.kingshot_name if player else "?",
            "event": event.name if event else "?",
            "start": s.local_start.strftime("%Y-%m-%d %H:%M"),
            "end": s.local_end.strftime("%Y-%m-%d %H:%M"),
            "needs_review": "Yes" if s.needs_review else "",
        })
    columns = [
        {"name": "player", "label": "Player", "field": "player", "sortable": True},
        {"name": "event", "label": "Event", "field": "event", "sortable": True},
        {"name": "start", "label": "Start", "field": "start", "sortable": True},
        {"name": "end", "label": "End", "field": "end"},
        {"name": "needs_review", "label": "Needs Review", "field": "needs_review"},
    ]
    ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")
    if not is_scheduler:
        ui.label("Showing your own players' time slots only.").classes("text-xs text-grey-5")


def _open_add_dialog() -> None:
    my_players = [p for p in players if p.account_id == role_switcher.current_account_id()] \
        if not role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN) else players

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Time Slot").classes("text-lg font-bold")
        player_select = ui.select(
            {p.id: p.kingshot_name for p in my_players}, label="Player"
        ).props("outlined").classes("w-full")
        event_select = ui.select(
            {e.id: e.name for e in events}, label="Event"
        ).props("outlined").classes("w-full")
        date_input = ui.date(value=datetime.utcnow().strftime("%Y-%m-%d")).classes("w-full")
        start_time = ui.time(value="12:00").classes("w-full")
        duration = ui.number("Duration (hours)", value=1, min=1, max=8).props("outlined").classes("w-full")

        def submit() -> None:
            if not (player_select.value and event_select.value):
                ui.notify("Select a player and event", type="warning")
                return
            start = datetime.strptime(f"{date_input.value} {start_time.value}", "%Y-%m-%d %H:%M")
            time_slots.append(TimeSlot(
                id=next_id(),
                player_id=player_select.value,
                event_id=event_select.value,
                local_start=start,
                local_end=start + timedelta(hours=duration.value or 1),
            ))
            dialog.close()
            slot_table.refresh()
            ui.notify("Time slot added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")

    dialog.open()
