from __future__ import annotations

from datetime import datetime

from nicegui import ui

from app.components import layout, role_switcher
from app.data import accounts as accounts_repo
from app.data import alliances as alliances_repo
from app.data import events as events_repo
from app.data import kingdoms as kingdoms_repo
from app.data import players as players_repo
from app.data import time_slots as time_slots_repo
from app.data.time_slots import TimeSlotOverlapError
from app.models.schema import Alliance, Event, Player, Role, TimeSlot, TimeSlotType
from app.pages.account_player import (
    _admin_alliance_ids, _format_dt, _render_field, _resolve_account_name, _set_enabled,
)
from app.utils.filters import get_id_filter, get_sort_state, get_text_filter, set_filter, set_sort_state
from app.utils.slot_times import (
    end_minutes, format_end_12h, format_end_24h, format_time_12h, picked_end_time, snap_to_quarter_hour,
    start_minutes, stored_end_time,
)

FILTER_KINGDOM_KEY = "timeslots_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "timeslots_filter_alliance_id"
FILTER_ACCOUNT_KEY = "timeslots_filter_account_id"
FILTER_PLAYER_KEY = "timeslots_filter_player_id"
FILTER_EVENT_KEY = "timeslots_filter_event_id"
FILTER_TYPE_KEY = "timeslots_filter_type"          # "" or a TimeSlotType value
FILTER_STATUS_KEY = "timeslots_filter_status"      # "" | "ok" (confirmed) | "needs" (needs confirmation)
SORT_BY_KEY = "timeslots_sort_by"
SORT_DESC_KEY = "timeslots_sort_desc"


async def _visible_players_for_slots() -> list[Player]:
    """Players whose time slots this viewer may see/manage.

    - SuperAdmin: everyone.
    - SchedulerAdmin: players in the alliance(s) of the previewed account's own
      players (any role) - the mock's role_switcher preview is a single
      account-wide setting, not tied to a specific player, so that's the
      stand-in for "their alliance" until real per-player role scoping exists
      (see account_player._admin_alliance_ids()).
    - Everyone else (User, Admin, PowerAdmin): their own account's players
      only - Admin/PowerAdmin get no extra reach on this page, per requirements
      (only SchedulerAdmin/SuperAdmin manage other accounts' time slots).

    Callers fetch this once per render and pass the result to the pure helpers
    below, rather than each helper hitting the DB again.
    """
    role = role_switcher.current_role()
    if role == Role.SUPER_ADMIN:
        return await players_repo.list_players()
    if role == Role.SCHEDULER_ADMIN:
        return await players_repo.list_players(alliance_ids=await _admin_alliance_ids())
    return await players_repo.list_players(account_ids=[role_switcher.current_account_id()])


async def _visible_slots(visible: list[Player]) -> list[TimeSlot]:
    """Every time slot belonging to a player this viewer can see - one query."""
    return await time_slots_repo.list_time_slots(player_ids=[p.player_id for p in visible])


def _show_kingdom_alliance_filter() -> bool:
    """Kingdom/Alliance dropdowns are SuperAdmin-only - every other role that can
    see this page is already scoped to at most one set of alliances (or none).
    """
    return role_switcher.current_role() == Role.SUPER_ADMIN


def _show_account_filter() -> bool:
    """Account dropdown is for SchedulerAdmin and SuperAdmin - the two roles that
    can see time slots belonging to more than one account.
    """
    return role_switcher.current_role() in (Role.SCHEDULER_ADMIN, Role.SUPER_ADMIN)


def _visibility_message() -> str | None:
    role = role_switcher.current_role()
    if role == Role.SUPER_ADMIN:
        return None
    if role == Role.SCHEDULER_ADMIN:
        return "Showing time slots for your alliance(s) only."
    return "Showing your own players' time slots only."


def _kingdom_ids_from_players(rows: list[Player], alliances: list[Alliance]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.alliance_id in alliance_ids}


def _players_matching(
    visible: list[Player],
    alliances: list[Alliance],
    *,
    kingdom_id: int | None = None,
    alliance_id: int | None = None,
    account_id: int | None = None,
    player_id: int | None = None,
) -> list[Player]:
    """`visible` narrowed by whichever of kingdom/alliance/account/player are
    given (`alliances` is the full alliance table, fetched once by the caller).
    Used to compute each filter dropdown's options from the *other* active
    filters, and to reconcile them, so all four stay mutually consistent - mirrors
    app/pages/players.py's _narrow(), extended with account and player levels
    since this page also filters down to a single account or player.
    """
    rows = visible
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.alliance_id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    if account_id is not None:
        rows = [p for p in rows if p.account_id == account_id]
    if player_id is not None:
        rows = [p for p in rows if p.player_id == player_id]
    return rows


def _structured_filters(
    visible: list[Player], alliances: list[Alliance]
) -> tuple[int | None, int | None, int | None, int | None]:
    """The stored (kingdom_id, alliance_id, account_id, player_id) filter values, each
    dropped to None unless it still matches a visible player - and Kingdom/Alliance/
    Account also to None when this role doesn't get that dropdown at all.
    """
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()
    return (
        get_id_filter(FILTER_KINGDOM_KEY, _kingdom_ids_from_players(visible, alliances)) if show_kingdom_alliance else None,
        get_id_filter(FILTER_ALLIANCE_KEY, {p.alliance_id for p in visible}) if show_kingdom_alliance else None,
        get_id_filter(FILTER_ACCOUNT_KEY, {p.account_id for p in visible}) if show_account else None,
        get_id_filter(FILTER_PLAYER_KEY, {p.player_id for p in visible}),
    )


def _filtered_slots(
    slots: list[TimeSlot], visible: list[Player], alliances: list[Alliance], events: list[Event]
) -> list[TimeSlot]:
    """`slots` (from _visible_slots()) narrowed by the active filters."""
    rows = slots
    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible, alliances)
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.event_id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    status_value = get_text_filter(FILTER_STATUS_KEY)

    # Kingdom/Alliance/Account/Player all narrow by player identity, so they're
    # applied together as a single "which players" restriction.
    if kingdom_id is not None or alliance_id is not None or account_id is not None or player_id is not None:
        matching_player_ids = {
            p.player_id for p in _players_matching(
                visible, alliances, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id, player_id=player_id,
            )
        }
        rows = [s for s in rows if s.player_id in matching_player_ids]
    if event_id is not None:
        rows = [s for s in rows if s.event_id == event_id]
    if type_value:
        rows = [s for s in rows if s.tslot_type.value == type_value]
    if status_value == "ok":
        rows = [s for s in rows if s.confirmed_ind]
    elif status_value == "needs":
        rows = [s for s in rows if not s.confirmed_ind]
    return rows


@ui.page("/timeslots")
async def timeslots_page() -> None:
    ui.page_title("Time Slots - Kingshot Scheduler")
    async with layout.frame("/timeslots"):
        ui.label("Time Slot Management").classes("text-2xl font-bold")
        await slot_filters()
        await slot_table()


@ui.refreshable
async def slot_filters() -> None:
    visible = await _visible_players_for_slots()
    kingdoms = await kingdoms_repo.list_kingdoms()
    alliances = await alliances_repo.list_alliances()
    events = await events_repo.list_events()
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()

    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible, alliances)
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.event_id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    status_value = get_text_filter(FILTER_STATUS_KEY)

    # Each of Kingdom/Alliance/Account/Player's options come from the *other* active
    # structured filters, so selecting any one narrows the rest - in every direction,
    # same mutual-cascade pattern as app/pages/players.py's player_filters().
    kingdom_option_ids = _kingdom_ids_from_players(
        _players_matching(visible, alliances, alliance_id=alliance_id, account_id=account_id, player_id=player_id),
        alliances,
    ) if show_kingdom_alliance else set()
    alliance_option_ids = {
        p.alliance_id for p in _players_matching(
            visible, alliances, kingdom_id=kingdom_id, account_id=account_id, player_id=player_id,
        )
    } if show_kingdom_alliance else set()
    account_option_ids = {
        p.account_id for p in _players_matching(
            visible, alliances, kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id,
        )
    } if show_account else set()
    player_options = {
        p.player_id: p.kingshot_name
        for p in _players_matching(visible, alliances, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
    }

    with ui.row().classes("w-full items-end gap-2"):
        # Filter order: Kingdom, Alliance, Account, Player, Event, Type, Status.
        # Kingdom/Alliance/Account only render for the roles that need them (see
        # _show_kingdom_alliance_filter()/_show_account_filter() above).
        kingdom_select = alliance_select = account_select = None
        if show_kingdom_alliance:
            kingdom_options = {k.kingdom_id: k.name for k in kingdoms if k.kingdom_id in kingdom_option_ids}
            kingdom_select = ui.select(
                kingdom_options, label="Kingdom", value=kingdom_id,
            ).props("outlined dense clearable").classes("w-40")

            alliance_options = {a.alliance_id: a.name for a in alliances if a.alliance_id in alliance_option_ids}
            alliance_select = ui.select(
                alliance_options, label="Alliance", value=alliance_id,
            ).props("outlined dense clearable").classes("w-40")

        if show_account:
            visible_accounts = await accounts_repo.list_accounts()
            account_options = {
                acc.account_id: acc.account_name for acc in visible_accounts if acc.account_id in account_option_ids
            }
            account_select = ui.select(
                account_options, label="Account", value=account_id,
            ).props("outlined dense clearable").classes("w-40")

        player_select = ui.select(
            player_options, label="Player", value=player_id,
        ).props("outlined dense clearable").classes("w-40")

        event_select = ui.select(
            {e.event_id: e.event_name for e in events}, label="Event", value=event_id,
        ).props("outlined dense clearable").classes("w-40")

        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            label="Type", value=type_value or None,
        ).props("outlined dense clearable").classes("w-36")

        status_select = ui.select(
            {"ok": "OK", "needs": "Needs Confirmation"}, label="Status", value=status_value or None,
        ).props("outlined dense clearable").classes("w-48")

        async def _apply_structured_change() -> None:
            """Shared tail for a Kingdom/Alliance/Account/Player change: clear any
            other selection that's no longer consistent with it, then refresh the
            filter row (so options + values catch up) and the table.
            """
            await _reconcile_filters()
            slot_filters.refresh()
            slot_table.refresh()

        async def on_kingdom_change() -> None:
            set_filter(FILTER_KINGDOM_KEY, kingdom_select.value)
            await _apply_structured_change()

        async def on_alliance_change() -> None:
            set_filter(FILTER_ALLIANCE_KEY, alliance_select.value)
            await _apply_structured_change()

        async def on_account_change() -> None:
            set_filter(FILTER_ACCOUNT_KEY, account_select.value)
            await _apply_structured_change()

        async def on_player_change() -> None:
            set_filter(FILTER_PLAYER_KEY, player_select.value)
            await _apply_structured_change()

        def on_event_change() -> None:
            set_filter(FILTER_EVENT_KEY, event_select.value)
            slot_table.refresh()

        def on_type_change() -> None:
            set_filter(FILTER_TYPE_KEY, type_select.value or "")
            slot_table.refresh()

        def on_status_change() -> None:
            set_filter(FILTER_STATUS_KEY, status_select.value or "")
            slot_table.refresh()

        if kingdom_select is not None:
            kingdom_select.on_value_change(on_kingdom_change)
        if alliance_select is not None:
            alliance_select.on_value_change(on_alliance_change)
        if account_select is not None:
            account_select.on_value_change(on_account_change)
        player_select.on_value_change(on_player_change)
        event_select.on_value_change(on_event_change)
        type_select.on_value_change(on_type_change)
        status_select.on_value_change(on_status_change)

        if kingdom_id is not None or alliance_id is not None or account_id is not None or player_id is not None \
                or event_id is not None or type_value or status_value:
            ui.button("Clear Filters", icon="close", on_click=_clear_slot_filters).props("flat dense")


async def _reconcile_filters() -> None:
    """Clears any structured filter (Kingdom/Alliance/Account/Player) whose stored
    value no longer has matching data given the other three - called after any of
    them changes, so all four stay mutually consistent regardless of which one you
    just touched. Mirrors app/pages/players.py's _reconcile_filters(), with Player
    added as the most granular level.
    """
    visible = await _visible_players_for_slots()
    alliances = await alliances_repo.list_alliances()
    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible, alliances)

    if player_id is not None:
        valid = {
            p.player_id for p in _players_matching(visible, alliances, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
        }
        if player_id not in valid:
            set_filter(FILTER_PLAYER_KEY, None)
            player_id = None
    if alliance_id is not None:
        valid = {
            p.alliance_id for p in _players_matching(visible, alliances, kingdom_id=kingdom_id, account_id=account_id, player_id=player_id)
        }
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(
            _players_matching(visible, alliances, alliance_id=alliance_id, account_id=account_id, player_id=player_id),
            alliances,
        )
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)
            kingdom_id = None
    if account_id is not None:
        valid = {
            p.account_id for p in _players_matching(visible, alliances, kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id)
        }
        if account_id not in valid:
            set_filter(FILTER_ACCOUNT_KEY, None)


def _clear_slot_filters() -> None:
    set_filter(FILTER_KINGDOM_KEY, None)
    set_filter(FILTER_ALLIANCE_KEY, None)
    set_filter(FILTER_ACCOUNT_KEY, None)
    set_filter(FILTER_PLAYER_KEY, None)
    set_filter(FILTER_EVENT_KEY, None)
    set_filter(FILTER_TYPE_KEY, "")
    set_filter(FILTER_STATUS_KEY, "")
    slot_filters.refresh()
    slot_table.refresh()




@ui.refreshable
async def slot_table() -> None:
    visible = await _visible_players_for_slots()
    alliances = await alliances_repo.list_alliances()
    events = await events_repo.list_events()
    slots = await _visible_slots(visible)
    filtered = _filtered_slots(slots, visible, alliances, events)
    event_name_by_id = {e.event_id: e.event_name for e in events}
    account_by_id = {a.account_id: a for a in await accounts_repo.list_accounts()}
    player_by_id = {p.player_id: p for p in visible}
    rows = []
    for s in filtered:
        player = player_by_id.get(s.player_id)
        # Guild-specific avatar if the player has one; else the account's global Discord
        # avatar; else None (renders as a generic person icon - same fallback chain as
        # the Player Management table).
        account = account_by_id.get(player.account_id) if player else None
        avatar_url = (player.discord_guild_avatar_url if player else None) or \
            (account.discord_avatar_url if account else None)
        rows.append({
            "id": s.tslot_id,
            "avatar_url": avatar_url,
            "player": player.kingshot_name if player else "?",
            "event": event_name_by_id.get(s.event_id, "?"),
            "start": s.start_time.strftime("%H:%M"),
            "end": format_end_24h(s.end_time),  # the picked end (stored end + 1s); midnight shows as 24:00
            "type": s.tslot_type.value,
            "confirmed": s.confirmed_ind,
        })
    columns = [
        {"name": "avatar_url", "label": "", "field": "avatar_url"},
        {"name": "player", "label": "Player", "field": "player", "sortable": True},
        {"name": "event", "label": "Event", "field": "event", "sortable": True},
        {"name": "start", "label": "Local Start", "field": "start", "sortable": True},
        {"name": "end", "label": "Local End", "field": "end"},
        {"name": "type", "label": "Type", "field": "type", "sortable": True},
        {"name": "confirmed", "label": "Status", "field": "confirmed", "sortable": True, "align": "center"},
    ]
    sort_by, sort_desc = get_sort_state(SORT_BY_KEY, SORT_DESC_KEY)

    # Toolbar: View/Edit act on the single selected row (see slot_by_id below);
    # both start disabled and are re-enabled only when selection count == 1 -
    # room to grow (e.g. a future multi-select "Delete") without restructuring.
    slot_by_id = {s.tslot_id: s for s in filtered}
    with ui.row().classes("w-full items-center gap-2"):
        view_button = ui.button("View", icon="visibility").props("outlined")
        edit_button = ui.button("Edit", icon="edit").props("outlined")
        ui.space()
        ui.button("Add Time Slot", icon="add", on_click=_open_add_dialog).props("unelevated color=primary")
    _set_enabled(view_button, False)
    _set_enabled(edit_button, False)

    table = ui.table(
        columns=columns, rows=rows, row_key="id", selection="multiple",
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
    # Status: a check mark when the slot is confirmed, an x when it needs (the owner's) confirmation.
    table.add_slot(
        "body-cell-confirmed",
        '''
        <q-td :props="props" class="text-center">
            <q-icon v-if="props.value" name="check" color="positive" size="sm">
                <q-tooltip>OK</q-tooltip>
            </q-icon>
            <q-icon v-else name="close" color="negative" size="sm">
                <q-tooltip>Needs confirmation</q-tooltip>
            </q-icon>
        </q-td>
        ''',
    )

    def on_pagination_change(e) -> None:
        payload = e.args[0] if isinstance(e.args, list) and e.args else e.args
        if not isinstance(payload, dict):
            return
        set_sort_state(SORT_BY_KEY, SORT_DESC_KEY, payload.get("sortBy"), bool(payload.get("descending", False)))

    table.on("update:pagination", on_pagination_change)

    def on_select(e) -> None:
        enabled = len(e.selection) == 1
        _set_enabled(view_button, enabled)
        _set_enabled(edit_button, enabled)

    table.on_select(on_select)

    async def handle_view() -> None:
        if len(table.selected) != 1:
            return
        slot = slot_by_id.get(table.selected[0]["id"])
        if slot:
            await _open_view_slot_dialog(slot)

    async def handle_edit() -> None:
        if len(table.selected) != 1:
            return
        slot = slot_by_id.get(table.selected[0]["id"])
        if slot:
            await _open_edit_slot_dialog(slot)

    view_button.on_click(handle_view)
    edit_button.on_click(handle_edit)

    if not filtered and slots:
        ui.label("No time slots match the current filters.").classes("text-sm text-grey-5")
    visibility_message = _visibility_message()
    if visibility_message:
        ui.label(visibility_message).classes("text-xs text-grey-5")


async def _render_slot_details(slot: TimeSlot) -> None:
    """Read-only detail view - every TimeSlot column. Shared verbatim between
    the View dialog and part 1 of the Edit dialog, mirroring
    players._render_player_details(). Times are shown as the user picked them
    (the stored end_time + 1 second - see app/utils/slot_times.py).
    """
    player = await players_repo.get_player(slot.player_id)
    event = await events_repo.get_event(slot.event_id)
    account = await accounts_repo.get_account(player.account_id) if player else None
    alliance = await alliances_repo.get_alliance(player.alliance_id) if player else None

    with ui.row().classes("items-center gap-3 w-full"):
        ui.icon("schedule", size="32px").classes("text-grey-6")
        ui.label(f"{player.kingshot_name if player else '?'} — {event.event_name if event else '?'}") \
            .classes("text-base font-bold")

    with ui.column().classes("w-full gap-1"):
        _render_field("Time Slot ID", str(slot.tslot_id))
        _render_field("Player", player.kingshot_name if player else f"Unknown (id={slot.player_id})")
        _render_field("Event", event.event_name if event else f"Unknown (id={slot.event_id})")
        _render_field("Alliance", alliance.name if alliance else "?")
        _render_field("Local Start", format_time_12h(slot.start_time))
        _render_field("Local End", format_end_12h(slot.end_time))
        _render_field("Type", slot.tslot_type.value.capitalize())
        _render_field("Status", "Confirmed" if slot.confirmed_ind else "Unconfirmed")

        ui.separator().classes("my-3")
        ui.label("Audit").classes("text-xs font-bold text-grey-6 uppercase")
        owner_time_zone = account.time_zone if account else "UTC"
        created_by = await _resolve_account_name(slot.create_account_id, account) if account else "—"
        _render_field("Created By", created_by)
        _render_field("Created At", _format_dt(slot.created_at, owner_time_zone))
        updated_by = await _resolve_account_name(slot.update_account_id, account) if account else "—"
        _render_field("Updated By", updated_by)
        _render_field("Updated At", _format_dt(slot.updated_at, owner_time_zone))


async def _open_view_slot_dialog(slot: TimeSlot) -> None:
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        ui.label("Time Slot Details").classes("text-lg font-bold")
        await _render_slot_details(slot)

        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=dialog.close).props("flat")

    dialog.open()


def _time_selects(*, start: tuple[int, int], end: tuple[int, int]) -> tuple[ui.select, ui.select, ui.select, ui.select]:
    """The Start/End hour + minute dropdowns shared by the Add and Edit dialogs, initialised to
    (hour, minute) pairs. The End values are the PICKED end (what the user sees), not the stored one;
    12 AM / 00 as an End means midnight (end of the day)."""
    hour_options = {h: datetime(2000, 1, 1, h).strftime("%I %p").lstrip("0") for h in range(24)}
    minute_options = {0: "00", 15: "15", 30: "30", 45: "45"}
    with ui.row().classes("w-full gap-2"):
        start_hour = ui.select(hour_options, value=start[0], label="Start Hour").props("outlined").classes("flex-1")
        start_minute = ui.select(minute_options, value=snap_to_quarter_hour(start[1]), label="Start Minute") \
            .props("outlined").classes("flex-1")
    with ui.row().classes("w-full gap-2"):
        end_hour = ui.select(hour_options, value=end[0], label="End Hour").props("outlined").classes("flex-1")
        end_minute = ui.select(minute_options, value=snap_to_quarter_hour(end[1]), label="End Minute") \
            .props("outlined").classes("flex-1")
    ui.label("An end of 12 AM / 00 means midnight (the end of the day).").classes("text-xs text-grey-6")
    return start_hour, start_minute, end_hour, end_minute


def _read_times(start_hour, start_minute, end_hour, end_minute):
    """(start_time, stored_end_time) from the dropdowns, or None (after warning) if the end isn't after the start."""
    if end_minutes(end_hour.value, end_minute.value) <= start_minutes(start_hour.value, start_minute.value):
        ui.notify("End time must be after start time", type="warning")
        return None
    return (
        datetime(2000, 1, 1, start_hour.value, start_minute.value).time(),
        stored_end_time(end_hour.value, end_minute.value),
    )


def _is_scheduler_or_super_admin() -> bool:
    return role_switcher.is_at_least(Role.SCHEDULER_ADMIN)


def _render_confirmation_control(slot: TimeSlot, *, is_owner: bool):
    """The Status row of the Edit dialog. Returns a zero-argument function giving the confirmed_ind
    value to save. The owning account can only move False -> True (the "Please confirm" checkbox);
    a SchedulerAdmin/SuperAdmin editing someone else's slot can only move True -> False (the
    "Request confirmation" toggle). If the viewer is both the owner and a scheduler/super admin,
    the owner rules win. Anyone else just sees the status.
    """
    if is_owner:
        if slot.confirmed_ind:
            _render_field("Status", "Confirmed")
            return lambda: True
        with ui.row().classes("w-full items-center gap-2"):
            ui.label("Please confirm").classes("text-sm text-grey-6 w-40 shrink-0")
            confirm_box = ui.checkbox(value=False)
        return lambda: confirm_box.value  # unchecked leaves the slot unconfirmed
    if _is_scheduler_or_super_admin():
        if slot.confirmed_ind:
            with ui.row().classes("w-full items-center gap-2"):
                ui.label("Request confirmation").classes("text-sm text-grey-6 w-40 shrink-0")
                request_toggle = ui.toggle({False: "No", True: "Yes"}, value=False)
            return lambda: not request_toggle.value  # Yes -> unconfirmed
        _render_field("Status", "Unconfirmed")
        return lambda: False
    _render_field("Status", "Confirmed" if slot.confirmed_ind else "Unconfirmed")
    return lambda: slot.confirmed_ind


async def _open_edit_slot_dialog(slot: TimeSlot) -> None:
    """Editable fields: start, end, type, and the confirmation status (see
    _render_confirmation_control() for who may change it, and how). Everything else is
    read-only (part 1, shared with the View dialog). End must be strictly after start,
    and the slot may not overlap another slot for the same player and event.
    """
    player = await players_repo.get_player(slot.player_id)
    is_owner = player is not None and player.account_id == role_switcher.current_account_id()
    picked_end = picked_end_time(slot.end_time)

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        ui.label("Edit Time Slot").classes("text-lg font-bold")

        @ui.refreshable
        async def details_view() -> None:
            await _render_slot_details(slot)

        await details_view()

        ui.separator().classes("my-3")
        ui.label("Update").classes("text-xs font-bold text-grey-6 uppercase")

        start_hour, start_minute, end_hour, end_minute = _time_selects(
            start=(slot.start_time.hour, slot.start_time.minute), end=(picked_end.hour, picked_end.minute),
        )
        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            value=slot.tslot_type.value, label="Type",
        ).props("outlined").classes("w-full")
        new_confirmed_ind = _render_confirmation_control(slot, is_owner=is_owner)

        async def submit() -> None:
            times = _read_times(start_hour, start_minute, end_hour, end_minute)
            if times is None:
                return
            try:
                await time_slots_repo.update_time_slot(
                    slot.tslot_id,
                    update_account_id=role_switcher.current_account_id(),
                    start_time=times[0],
                    end_time=times[1],
                    tslot_type=TimeSlotType(type_select.value),
                    confirmed_ind=new_confirmed_ind(),
                )
            except TimeSlotOverlapError as e:
                ui.notify(str(e), type="warning")
                return
            dialog.close()
            slot_filters.refresh()
            slot_table.refresh()
            ui.notify("Time slot updated", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", on_click=submit).props("unelevated color=primary")

    dialog.open()


async def _open_add_dialog() -> None:
    my_players = await _visible_players_for_slots()
    events = await events_repo.list_events()
    account_id_by_player_id = {p.player_id: p.account_id for p in my_players}

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Time Slot").classes("text-lg font-bold")
        player_select = ui.select(
            {p.player_id: p.kingshot_name for p in my_players}, label="Player"
        ).props("outlined").classes("w-full")
        event_select = ui.select(
            {e.event_id: e.event_name for e in events}, label="Event"
        ).props("outlined").classes("w-full")
        # Time-only, no date - this is a recurring local-time availability window (see schema.TimeSlot).
        # Two dropdowns instead of ui.time()'s clock-face picker, same hour+minute pattern as the
        # Edit dialog. Default: 12 PM - 1 PM.
        start_hour, start_minute, end_hour, end_minute = _time_selects(start=(12, 0), end=(13, 0))
        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            value=TimeSlotType.PREFERRED.value, label="Type",
        ).props("outlined").classes("w-full")
        # A new slot is always confirmed - nobody gets the "request confirmation" toggle here.
        _render_field("Status", "Confirmed")

        async def submit() -> None:
            if not (player_select.value and event_select.value):
                ui.notify("Select a player and event", type="warning")
                return
            times = _read_times(start_hour, start_minute, end_hour, end_minute)
            if times is None:
                return
            # create_account_id follows the same "None = added by the owner" convention as
            # Player.create_account_id; update_account_id always records whoever is acting.
            acting_account_id = role_switcher.current_account_id()
            owner_account_id = account_id_by_player_id[player_select.value]
            try:
                await time_slots_repo.create_time_slot(
                    player_id=player_select.value,
                    event_id=event_select.value,
                    start_time=times[0],
                    end_time=times[1],
                    tslot_type=TimeSlotType(type_select.value),
                    create_account_id=None if acting_account_id == owner_account_id else acting_account_id,
                    update_account_id=acting_account_id,
                )
            except TimeSlotOverlapError as e:
                ui.notify(str(e), type="warning")
                return
            dialog.close()
            slot_filters.refresh()
            slot_table.refresh()
            ui.notify("Time slot added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")

    dialog.open()
