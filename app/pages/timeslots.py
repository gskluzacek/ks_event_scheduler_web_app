from __future__ import annotations

from datetime import datetime, timedelta

from nicegui import ui

from app.components import layout, role_switcher
from app.models.sample_data import accounts, events, players, time_slots
from app.models.schema import Player, Role, TimeSlot, TimeSlotType, next_id
from app.utils.filters import get_id_filter, get_sort_state, get_text_filter, set_filter, set_sort_state

FILTER_PLAYER_KEY = "timeslots_filter_player_id"
FILTER_EVENT_KEY = "timeslots_filter_event_id"
FILTER_TYPE_KEY = "timeslots_filter_type"          # "" or a TimeSlotType value
FILTER_REVIEW_KEY = "timeslots_filter_needs_review"  # "" | "yes" | "no"
SORT_BY_KEY = "timeslots_sort_by"
SORT_DESC_KEY = "timeslots_sort_desc"


def _visible_slots() -> list[TimeSlot]:
    if role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN):
        return time_slots
    my_player_ids = {p.id for p in players if p.account_id == role_switcher.current_account_id()}
    return [s for s in time_slots if s.player_id in my_player_ids]


def _filterable_players() -> list[Player]:
    """Players offered in the Player filter dropdown - same scoping as _visible_slots()."""
    if role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN):
        return players
    return [p for p in players if p.account_id == role_switcher.current_account_id()]


def _filtered_slots() -> list[TimeSlot]:
    rows = _visible_slots()
    player_id = get_id_filter(FILTER_PLAYER_KEY, {p.id for p in _filterable_players()})
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    if player_id is not None:
        rows = [s for s in rows if s.player_id == player_id]
    if event_id is not None:
        rows = [s for s in rows if s.event_id == event_id]
    if type_value:
        rows = [s for s in rows if s.time_slot_type.value == type_value]
    if review_value == "yes":
        rows = [s for s in rows if s.needs_review]
    elif review_value == "no":
        rows = [s for s in rows if not s.needs_review]
    return rows


@ui.page("/timeslots")
def timeslots_page() -> None:
    ui.page_title("Time Slots - Kingshot Scheduler")
    with layout.frame("/timeslots"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Time Slot Management").classes("text-2xl font-bold")
            ui.button("Add Time Slot", icon="add", on_click=_open_add_dialog).props("unelevated color=primary")
        slot_filters()
        slot_table()


@ui.refreshable
def slot_filters() -> None:
    filterable_players = _filterable_players()
    player_id = get_id_filter(FILTER_PLAYER_KEY, {p.id for p in filterable_players})
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    with ui.row().classes("w-full items-end gap-2"):
        player_select = ui.select(
            {p.id: p.kingshot_name for p in filterable_players}, label="Player", value=player_id,
        ).props("outlined dense clearable").classes("w-44")

        event_select = ui.select(
            {e.id: e.name for e in events}, label="Event", value=event_id,
        ).props("outlined dense clearable").classes("w-44")

        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            label="Type", value=type_value or None,
        ).props("outlined dense clearable").classes("w-36")

        review_select = ui.select(
            {"yes": "Yes", "no": "No"}, label="Needs Review", value=review_value or None,
        ).props("outlined dense clearable").classes("w-36")

        def on_player_change() -> None:
            set_filter(FILTER_PLAYER_KEY, player_select.value)
            slot_table.refresh()

        def on_event_change() -> None:
            set_filter(FILTER_EVENT_KEY, event_select.value)
            slot_table.refresh()

        def on_type_change() -> None:
            set_filter(FILTER_TYPE_KEY, type_select.value or "")
            slot_table.refresh()

        def on_review_change() -> None:
            set_filter(FILTER_REVIEW_KEY, review_select.value or "")
            slot_table.refresh()

        player_select.on_value_change(on_player_change)
        event_select.on_value_change(on_event_change)
        type_select.on_value_change(on_type_change)
        review_select.on_value_change(on_review_change)

        if player_id is not None or event_id is not None or type_value or review_value:
            ui.button("Clear Filters", icon="close", on_click=_clear_slot_filters).props("flat dense")


def _clear_slot_filters() -> None:
    set_filter(FILTER_PLAYER_KEY, None)
    set_filter(FILTER_EVENT_KEY, None)
    set_filter(FILTER_TYPE_KEY, "")
    set_filter(FILTER_REVIEW_KEY, "")
    slot_filters.refresh()
    slot_table.refresh()


@ui.refreshable
def slot_table() -> None:
    is_scheduler = role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN)
    filtered = _filtered_slots()
    account_by_id = {a.id: a for a in accounts}
    rows = []
    for s in filtered:
        player = next((p for p in players if p.id == s.player_id), None)
        event = next((e for e in events if e.id == s.event_id), None)
        # Guild-specific avatar if the player has one; else the account's global Discord
        # avatar; else None (renders as a generic person icon - same fallback chain as
        # the Player Management table).
        account = account_by_id.get(player.account_id) if player else None
        avatar_url = (player.discord_guild_avatar_url if player else None) or \
            (account.discord_avatar_url if account else None)
        rows.append({
            "id": s.id,
            "avatar_url": avatar_url,
            "player": player.kingshot_name if player else "?",
            "event": event.name if event else "?",
            "start": s.local_start.strftime("%H:%M"),
            "end": s.local_end.strftime("%H:%M"),
            "type": s.time_slot_type.value,
            "needs_review": "Yes" if s.needs_review else "",
        })
    columns = [
        {"name": "avatar_url", "label": "", "field": "avatar_url"},
        {"name": "player", "label": "Player", "field": "player", "sortable": True},
        {"name": "event", "label": "Event", "field": "event", "sortable": True},
        {"name": "start", "label": "Local Start", "field": "start", "sortable": True},
        {"name": "end", "label": "Local End", "field": "end"},
        {"name": "type", "label": "Type", "field": "type", "sortable": True},
        {"name": "needs_review", "label": "Needs Review", "field": "needs_review"},
    ]
    sort_by, sort_desc = get_sort_state(SORT_BY_KEY, SORT_DESC_KEY)
    table = ui.table(
        columns=columns, rows=rows, row_key="id",
        pagination={"sortBy": sort_by, "descending": sort_desc, "rowsPerPage": 0},
    ).classes("w-full").props("flat bordered")
    # Custom cell: q-avatar with the player's Discord image if we have one, else a generic
    # icon. Same slot pattern as app/pages/accounts.py and app/pages/players.py.
    table.add_slot(
        "body-cell-avatar_url",
        '''
        <q-td :props="props">
            <q-avatar size="28px" color="grey-4" text-color="grey-8">
                <img v-if="props.value" :src="props.value" style="width: 100%; height: 100%; object-fit: cover" />
                <q-icon v-else name="person" />
            </q-avatar>
        </q-td>
        ''',
    )

    def on_pagination_change(e) -> None:
        payload = e.args[0] if isinstance(e.args, list) and e.args else e.args
        if not isinstance(payload, dict):
            return
        set_sort_state(SORT_BY_KEY, SORT_DESC_KEY, payload.get("sortBy"), bool(payload.get("descending", False)))

    table.on("update:pagination", on_pagination_change)

    if not filtered and _visible_slots():
        ui.label("No time slots match the current filters.").classes("text-sm text-grey-5")
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
        # Time-only, no date - this is a recurring local-time availability window (see schema.TimeSlot).
        # Two dropdowns instead of ui.time()'s clock-face picker, per request.
        hour_options = {h: datetime(2000, 1, 1, h).strftime("%I %p").lstrip("0") for h in range(24)}
        minute_options = {0: "00", 15: "15", 30: "30", 45: "45"}
        with ui.row().classes("w-full gap-2"):
            hour_select = ui.select(hour_options, value=12, label="Start Hour") \
                .props("outlined").classes("flex-1")
            minute_select = ui.select(minute_options, value=0, label="Start Minute") \
                .props("outlined").classes("flex-1")
        duration = ui.number("Duration (hours)", value=1, min=1, max=8).props("outlined").classes("w-full")
        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            value=TimeSlotType.PREFERRED.value, label="Type",
        ).props("outlined").classes("w-full")

        def submit() -> None:
            if not (player_select.value and event_select.value):
                ui.notify("Select a player and event", type="warning")
                return
            # Combine with an arbitrary anchor date purely to do time arithmetic, then drop it again.
            start_dt = datetime(2000, 1, 1, hour_select.value, minute_select.value)
            end_dt = start_dt + timedelta(hours=duration.value or 1)
            time_slots.append(TimeSlot(
                id=next_id(),
                player_id=player_select.value,
                event_id=event_select.value,
                local_start=start_dt.time(),
                local_end=end_dt.time(),
                time_slot_type=TimeSlotType(type_select.value),
            ))
            dialog.close()
            slot_table.refresh()
            ui.notify("Time slot added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")

    dialog.open()
