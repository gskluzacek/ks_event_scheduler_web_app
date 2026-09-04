from __future__ import annotations

from datetime import datetime, timedelta

from nicegui import ui

from app.components import layout, role_switcher
from app.models.sample_data import accounts, alliances, events, kingdoms, players, time_slots
from app.models.schema import Player, Role, TimeSlot, TimeSlotType, next_id
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


def _scheduler_admin_alliance_ids() -> set[int]:
    """The alliance(s) a SchedulerAdmin manages, derived from the *previewed
    account's* players (any role, not just SchedulerAdmin ones) - the mock's
    role_switcher preview is a single account-wide setting, not tied to a
    specific player, so this is the stand-in for "their alliance" until real
    per-player role scoping exists.
    """
    account_id = role_switcher.current_account_id()
    return {p.alliance_id for p in players if p.account_id == account_id}


def _visible_players_for_slots() -> list[Player]:
    """Players whose time slots this viewer may see/manage.

    - SuperAdmin: everyone.
    - SchedulerAdmin: players in the previewed account's alliance(s) - see
      _scheduler_admin_alliance_ids().
    - Everyone else (User, Admin, PowerAdmin): their own account's players
      only - Admin/PowerAdmin get no extra reach on this page, per requirements
      (only SchedulerAdmin/SuperAdmin manage other accounts' time slots).
    """
    role = role_switcher.current_role()
    if role == Role.SUPER_ADMIN:
        return players
    if role == Role.SCHEDULER_ADMIN:
        alliance_ids = _scheduler_admin_alliance_ids()
        return [p for p in players if p.alliance_id in alliance_ids]
    account_id = role_switcher.current_account_id()
    return [p for p in players if p.account_id == account_id]


def _visible_slots() -> list[TimeSlot]:
    visible_player_ids = {p.id for p in _visible_players_for_slots()}
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


def _visible_kingdom_ids() -> set[int]:
    alliance_ids = {p.alliance_id for p in _visible_players_for_slots()}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _visible_alliance_ids() -> set[int]:
    return {p.alliance_id for p in _visible_players_for_slots()}


def _visible_account_ids() -> set[int]:
    return {p.account_id for p in _visible_players_for_slots()}


def _visible_players_matching(
    *,
    kingdom_id: int | None = None,
    alliance_id: int | None = None,
    account_id: int | None = None,
    player_id: int | None = None,
) -> list[Player]:
    """Visible players narrowed by whichever of kingdom/alliance/account/player are
    given. Used to compute each filter dropdown's options from the *other* active
    filters, and to reconcile them, so all four stay mutually consistent - mirrors
    app/pages/players.py's _visible_players_matching(), extended with a player_id
    level since this page also filters down to a single player.
    """
    rows = _visible_players_for_slots()
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    if account_id is not None:
        rows = [p for p in rows if p.account_id == account_id]
    if player_id is not None:
        rows = [p for p in rows if p.id == player_id]
    return rows


def _kingdom_ids_from_players(rows: list[Player]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _filtered_slots() -> list[TimeSlot]:
    rows = _visible_slots()
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()

    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids()) if show_kingdom_alliance else None
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids()) if show_kingdom_alliance else None
    account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids()) if show_account else None
    player_id = get_id_filter(FILTER_PLAYER_KEY, {p.id for p in _visible_players_for_slots()})
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    # Kingdom/Alliance/Account/Player all narrow by player identity, so they're
    # applied together as a single "which players" restriction.
    if kingdom_id is not None or alliance_id is not None or account_id is not None or player_id is not None:
        matching_player_ids = {
            p.id for p in _visible_players_matching(
                kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id, player_id=player_id,
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
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()

    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids()) if show_kingdom_alliance else None
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids()) if show_kingdom_alliance else None
    account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids()) if show_account else None
    player_id = get_id_filter(FILTER_PLAYER_KEY, {p.id for p in _visible_players_for_slots()})
    event_id = get_id_filter(FILTER_EVENT_KEY, {e.id for e in events})
    type_value = get_text_filter(FILTER_TYPE_KEY)
    review_value = get_text_filter(FILTER_REVIEW_KEY)

    # Each of Kingdom/Alliance/Account/Player's options come from the *other* active
    # structured filters, so selecting any one narrows the rest - in every direction,
    # same mutual-cascade pattern as app/pages/players.py's player_filters().
    kingdom_option_ids = _kingdom_ids_from_players(
        _visible_players_matching(alliance_id=alliance_id, account_id=account_id, player_id=player_id)
    ) if show_kingdom_alliance else set()
    alliance_option_ids = {
        p.alliance_id for p in _visible_players_matching(
            kingdom_id=kingdom_id, account_id=account_id, player_id=player_id,
        )
    } if show_kingdom_alliance else set()
    account_option_ids = {
        p.account_id for p in _visible_players_matching(
            kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id,
        )
    } if show_account else set()
    player_option_ids = {
        p.id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
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
            account_options = {acc.id: acc.account_name for acc in accounts if acc.id in account_option_ids}
            account_select = ui.select(
                account_options, label="Account", value=account_id,
            ).props("outlined dense clearable").classes("w-40")

        player_options = {p.id: p.kingshot_name for p in players if p.id in player_option_ids}
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

        def _apply_structured_change() -> None:
            """Shared tail for a Kingdom/Alliance/Account/Player change: clear any
            other selection that's no longer consistent with it, then refresh the
            filter row (so options + values catch up) and the table.
            """
            _reconcile_filters()
            slot_filters.refresh()
            slot_table.refresh()

        def on_kingdom_change() -> None:
            set_filter(FILTER_KINGDOM_KEY, kingdom_select.value)
            _apply_structured_change()

        def on_alliance_change() -> None:
            set_filter(FILTER_ALLIANCE_KEY, alliance_select.value)
            _apply_structured_change()

        def on_account_change() -> None:
            set_filter(FILTER_ACCOUNT_KEY, account_select.value)
            _apply_structured_change()

        def on_player_change() -> None:
            set_filter(FILTER_PLAYER_KEY, player_select.value)
            _apply_structured_change()

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


def _reconcile_filters() -> None:
    """Clears any structured filter (Kingdom/Alliance/Account/Player) whose stored
    value no longer has matching data given the other three - called after any of
    them changes, so all four stay mutually consistent regardless of which one you
    just touched. Mirrors app/pages/players.py's _reconcile_filters(), with Player
    added as the most granular level.
    """
    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_account = _show_account_filter()

    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids()) if show_kingdom_alliance else None
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids()) if show_kingdom_alliance else None
    account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids()) if show_account else None
    player_id = get_id_filter(FILTER_PLAYER_KEY, {p.id for p in _visible_players_for_slots()})

    if player_id is not None:
        valid = {
            p.id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id, account_id=account_id)
        }
        if player_id not in valid:
            set_filter(FILTER_PLAYER_KEY, None)
            player_id = None
    if alliance_id is not None:
        valid = {
            p.alliance_id for p in _visible_players_matching(kingdom_id=kingdom_id, account_id=account_id, player_id=player_id)
        }
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(
            _visible_players_matching(alliance_id=alliance_id, account_id=account_id, player_id=player_id)
        )
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)
            kingdom_id = None
    if account_id is not None:
        valid = {
            p.account_id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id, player_id=player_id)
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
def slot_table() -> None:
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
    visibility_message = _visibility_message()
    if visibility_message:
        ui.label(visibility_message).classes("text-xs text-grey-5")


def _open_add_dialog() -> None:
    my_players = _visible_players_for_slots()

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
            slot_filters.refresh()
            slot_table.refresh()
            ui.notify("Time slot added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add", on_click=submit).props("unelevated color=primary")

    dialog.open()
