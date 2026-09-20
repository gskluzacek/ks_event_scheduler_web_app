from __future__ import annotations

from datetime import datetime

from nicegui import ui

from app.components import layout, role_switcher
from app.data import accounts as accounts_repo
from app.data import players as players_repo
from app.models.sample_data import alliances, events, kingdoms, time_slots
from app.models.schema import Player, Role, TimeSlot, TimeSlotType, next_id
from app.pages.account_player import (
    _admin_alliance_ids, _format_dt, _render_field, _resolve_account_name, _set_enabled,
)
from app.utils.filters import get_id_filter, get_sort_state, get_text_filter, set_filter, set_sort_state

FILTER_KINGDOM_KEY = "timeslots_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "timeslots_filter_alliance_id"
FILTER_ACCOUNT_KEY = "timeslots_filter_account_id"
FILTER_PLAYER_KEY = "timeslots_filter_player_id"
FILTER_EVENT_KEY = "timeslots_filter_event_id"
FILTER_TYPE_KEY = "timeslots_filter_type"          # "" or a TimeSlotType value
FILTER_REVIEW_KEY = "timeslots_filter_needs_review"  # "" | "yes" | "no"
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


def _visible_slots(visible: list[Player]) -> list[TimeSlot]:
    visible_player_ids = {p.player_id for p in visible}
    return [s for s in time_slots if s.player_id in visible_player_ids]


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


def _kingdom_ids_from_players(rows: list[Player]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _players_matching(
    visible: list[Player],
    *,
    kingdom_id: int | None = None,
    alliance_id: int | None = None,
    account_id: int | None = None,
    player_id: int | None = None,
) -> list[Player]:
    """`visible` narrowed by whichever of kingdom/alliance/account/player are
    given. Used to compute each filter dropdown's options from the *other* active
    filters, and to reconcile them, so all four stay mutually consistent - mirrors
    app/pages/players.py's _narrow(), extended with account and player levels
    since this page also filters down to a single account or player.
    """
    rows = visible
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    if account_id is not None:
        rows = [p for p in rows if p.account_id == account_id]
    if player_id is not None:
        rows = [p for p in rows if p.player_id == player_id]
    return rows


def _structured_filters(visible: list[Player]) -> tuple[int | None, int | None, int | None, int | None]:
    """The stored (kingdom_id, alliance_id, account_id, player_id) filter values, each
    dropped to None unless it still matches a visible player - and Kingdom/Alliance/
    Account also to None when this role doesn't get that dropdown at all.
    """
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()
    return (
        get_id_filter(FILTER_KINGDOM_KEY, _kingdom_ids_from_players(visible)) if show_kingdom_alliance else None,
        get_id_filter(FILTER_ALLIANCE_KEY, {p.alliance_id for p in visible}) if show_kingdom_alliance else None,
        get_id_filter(FILTER_ACCOUNT_KEY, {p.account_id for p in visible}) if show_account else None,
        get_id_filter(FILTER_PLAYER_KEY, {p.player_id for p in visible}),
    )


def _filtered_slots(visible: list[Player]) -> list[TimeSlot]:
    rows = _visible_slots(visible)
    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible)
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    # Kingdom/Alliance/Account/Player all narrow by player identity, so they're
    # applied together as a single "which players" restriction.
    if kingdom_id is not None or alliance_id is not None or account_id is not None or player_id is not None:
        matching_player_ids = {
            p.player_id for p in _players_matching(
                visible, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id, player_id=player_id,
            )
        }
        rows = [s for s in rows if s.player_id in matching_player_ids]
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
async def timeslots_page() -> None:
    ui.page_title("Time Slots - Kingshot Scheduler")
    async with layout.frame("/timeslots"):
        ui.label("Time Slot Management").classes("text-2xl font-bold")
        await slot_filters()
        await slot_table()


@ui.refreshable
async def slot_filters() -> None:
    visible = await _visible_players_for_slots()
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()

    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible)
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    # Each of Kingdom/Alliance/Account/Player's options come from the *other* active
    # structured filters, so selecting any one narrows the rest - in every direction,
    # same mutual-cascade pattern as app/pages/players.py's player_filters().
    kingdom_option_ids = _kingdom_ids_from_players(
        _players_matching(visible, alliance_id=alliance_id, account_id=account_id, player_id=player_id)
    ) if show_kingdom_alliance else set()
    alliance_option_ids = {
        p.alliance_id for p in _players_matching(
            visible, kingdom_id=kingdom_id, account_id=account_id, player_id=player_id,
        )
    } if show_kingdom_alliance else set()
    account_option_ids = {
        p.account_id for p in _players_matching(
            visible, kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id,
        )
    } if show_account else set()
    player_options = {
        p.player_id: p.kingshot_name
        for p in _players_matching(visible, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
    }

    with ui.row().classes("w-full items-end gap-2"):
        # Filter order: Kingdom, Alliance, Account, Player, Event, Type, Needs Review.
        # Kingdom/Alliance/Account only render for the roles that need them (see
        # _show_kingdom_alliance_filter()/_show_account_filter() above).
        kingdom_select = alliance_select = account_select = None
        if show_kingdom_alliance:
            kingdom_options = {k.id: k.name for k in kingdoms if k.id in kingdom_option_ids}
            kingdom_select = ui.select(
                kingdom_options, label="Kingdom", value=kingdom_id,
            ).props("outlined dense clearable").classes("w-40")

            alliance_options = {a.id: a.name for a in alliances if a.id in alliance_option_ids}
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
            {e.id: e.name for e in events}, label="Event", value=event_id,
        ).props("outlined dense clearable").classes("w-40")

        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            label="Type", value=type_value or None,
        ).props("outlined dense clearable").classes("w-36")

        review_select = ui.select(
            {"yes": "Yes", "no": "No"}, label="Needs Review", value=review_value or None,
        ).props("outlined dense clearable").classes("w-36")

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

        def on_review_change() -> None:
            set_filter(FILTER_REVIEW_KEY, review_select.value or "")
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
        review_select.on_value_change(on_review_change)

        if kingdom_id is not None or alliance_id is not None or account_id is not None or player_id is not None \
                or event_id is not None or type_value or review_value:
            ui.button("Clear Filters", icon="close", on_click=_clear_slot_filters).props("flat dense")


async def _reconcile_filters() -> None:
    """Clears any structured filter (Kingdom/Alliance/Account/Player) whose stored
    value no longer has matching data given the other three - called after any of
    them changes, so all four stay mutually consistent regardless of which one you
    just touched. Mirrors app/pages/players.py's _reconcile_filters(), with Player
    added as the most granular level.
    """
    visible = await _visible_players_for_slots()
    kingdom_id, alliance_id, account_id, player_id = _structured_filters(visible)

    if player_id is not None:
        valid = {
            p.player_id for p in _players_matching(visible, kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
        }
        if player_id not in valid:
            set_filter(FILTER_PLAYER_KEY, None)
            player_id = None
    if alliance_id is not None:
        valid = {
            p.alliance_id for p in _players_matching(visible, kingdom_id=kingdom_id, account_id=account_id, player_id=player_id)
        }
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(
            _players_matching(visible, alliance_id=alliance_id, account_id=account_id, player_id=player_id)
        )
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)
            kingdom_id = None
    if account_id is not None:
        valid = {
            p.account_id for p in _players_matching(visible, kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id)
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
    set_filter(FILTER_REVIEW_KEY, "")
    slot_filters.refresh()
    slot_table.refresh()


@ui.refreshable
async def slot_table() -> None:
    visible = await _visible_players_for_slots()
    filtered = _filtered_slots(visible)
    account_by_id = {a.account_id: a for a in await accounts_repo.list_accounts()}
    player_by_id = {p.player_id: p for p in visible}
    rows = []
    for s in filtered:
        player = player_by_id.get(s.player_id)
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

    # Toolbar: View/Edit act on the single selected row (see slot_by_id below);
    # both start disabled and are re-enabled only when selection count == 1 -
    # room to grow (e.g. a future multi-select "Delete") without restructuring.
    slot_by_id = {s.id: s for s in filtered}
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

    if not filtered and _visible_slots(visible):
        ui.label("No time slots match the current filters.").classes("text-sm text-grey-5")
    visibility_message = _visibility_message()
    if visibility_message:
        ui.label(visibility_message).classes("text-xs text-grey-5")


async def _render_slot_details(slot: TimeSlot) -> None:
    """Read-only detail view - every TimeSlot column. Shared verbatim between
    the View dialog and part 1 of the Edit dialog, mirroring
    players._render_player_details().
    """
    player = await players_repo.get_player(slot.player_id)
    event = next((e for e in events if e.id == slot.event_id), None)
    account = await accounts_repo.get_account(player.account_id) if player else None
    alliance = next((a for a in alliances if a.id == player.alliance_id), None) if player else None

    with ui.row().classes("items-center gap-3 w-full"):
        ui.icon("schedule", size="32px").classes("text-grey-6")
        ui.label(f"{player.kingshot_name if player else '?'} — {event.name if event else '?'}") \
            .classes("text-base font-bold")

    with ui.column().classes("w-full gap-1"):
        _render_field("Time Slot ID", str(slot.id))
        _render_field("Player", player.kingshot_name if player else f"Unknown (id={slot.player_id})")
        _render_field("Event", event.name if event else f"Unknown (id={slot.event_id})")
        _render_field("Alliance", alliance.name if alliance else "?")
        _render_field("Local Start", slot.local_start.strftime("%I:%M %p").lstrip("0"))
        _render_field("Local End", slot.local_end.strftime("%I:%M %p").lstrip("0"))
        _render_field("Type", slot.time_slot_type.value.capitalize())
        _render_field("Needs Review", "Yes" if slot.needs_review else "No")

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


async def _open_edit_slot_dialog(slot: TimeSlot) -> None:
    """Editable fields per requirements: local_start, local_end, time_slot_type,
    needs_review. Everything else is read-only (part 1, shared with the View
    dialog). Start/end use the same hour+minute dropdown pattern as the Add
    dialog. End must be strictly after start - overnight windows (e.g.
    23:00-01:00) aren't supported, same restriction as _open_add_dialog.
    """
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        ui.label("Edit Time Slot").classes("text-lg font-bold")

        @ui.refreshable
        async def details_view() -> None:
            await _render_slot_details(slot)

        await details_view()

        ui.separator().classes("my-3")
        ui.label("Update").classes("text-xs font-bold text-grey-6 uppercase")

        hour_options = {h: datetime(2000, 1, 1, h).strftime("%I %p").lstrip("0") for h in range(24)}
        minute_options = {0: "00", 15: "15", 30: "30", 45: "45"}

        with ui.row().classes("w-full gap-2"):
            start_hour_select = ui.select(hour_options, value=slot.local_start.hour, label="Start Hour") \
                .props("outlined").classes("flex-1")
            start_minute_select = ui.select(minute_options, value=slot.local_start.minute, label="Start Minute") \
                .props("outlined").classes("flex-1")
        with ui.row().classes("w-full gap-2"):
            end_hour_select = ui.select(hour_options, value=slot.local_end.hour, label="End Hour") \
                .props("outlined").classes("flex-1")
            end_minute_select = ui.select(minute_options, value=slot.local_end.minute, label="End Minute") \
                .props("outlined").classes("flex-1")
        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            value=slot.time_slot_type.value, label="Type",
        ).props("outlined").classes("w-full")
        needs_review_checkbox = ui.checkbox("Needs Review", value=slot.needs_review)

        def submit() -> None:
            start_time = datetime(2000, 1, 1, start_hour_select.value, start_minute_select.value).time()
            end_time = datetime(2000, 1, 1, end_hour_select.value, end_minute_select.value).time()
            if end_time <= start_time:
                ui.notify("End time must be after start time", type="warning")
                return
            slot.local_start = start_time
            slot.local_end = end_time
            slot.time_slot_type = TimeSlotType(type_select.value)
            slot.needs_review = needs_review_checkbox.value
            slot.update_account_id = role_switcher.current_account_id()
            slot.updated_at = datetime.utcnow()
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

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Time Slot").classes("text-lg font-bold")
        player_select = ui.select(
            {p.player_id: p.kingshot_name for p in my_players}, label="Player"
        ).props("outlined").classes("w-full")
        event_select = ui.select(
            {e.id: e.name for e in events}, label="Event"
        ).props("outlined").classes("w-full")
        # Time-only, no date - this is a recurring local-time availability window (see schema.TimeSlot).
        # Two dropdowns instead of ui.time()'s clock-face picker, per request. Same hour+minute
        # dropdown pattern as the Edit dialog, for both start and end.
        hour_options = {h: datetime(2000, 1, 1, h).strftime("%I %p").lstrip("0") for h in range(24)}
        minute_options = {0: "00", 15: "15", 30: "30", 45: "45"}
        with ui.row().classes("w-full gap-2"):
            start_hour_select = ui.select(hour_options, value=12, label="Start Hour") \
                .props("outlined").classes("flex-1")
            start_minute_select = ui.select(minute_options, value=0, label="Start Minute") \
                .props("outlined").classes("flex-1")
        with ui.row().classes("w-full gap-2"):
            end_hour_select = ui.select(hour_options, value=13, label="End Hour") \
                .props("outlined").classes("flex-1")
            end_minute_select = ui.select(minute_options, value=0, label="End Minute") \
                .props("outlined").classes("flex-1")
        type_select = ui.select(
            {t.value: t.value.capitalize() for t in TimeSlotType},
            value=TimeSlotType.PREFERRED.value, label="Type",
        ).props("outlined").classes("w-full")

        def submit() -> None:
            if not (player_select.value and event_select.value):
                ui.notify("Select a player and event", type="warning")
                return
            start_time = datetime(2000, 1, 1, start_hour_select.value, start_minute_select.value).time()
            end_time = datetime(2000, 1, 1, end_hour_select.value, end_minute_select.value).time()
            if end_time <= start_time:
                ui.notify("End time must be after start time", type="warning")
                return
            time_slots.append(TimeSlot(
                id=next_id(),
                player_id=player_select.value,
                event_id=event_select.value,
                local_start=start_time,
                local_end=end_time,
                time_slot_type=TimeSlotType(type_select.value),
            ))
            dialog.close()
            slot_filters.refresh()
            slot_table.refresh()
            ui.notify("Time slot added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")

    dialog.open()
