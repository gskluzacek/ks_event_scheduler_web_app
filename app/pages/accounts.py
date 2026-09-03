from __future__ import annotations

from nicegui import ui

from app.components import layout, role_switcher
from app.components.timezone_select import TimeZoneSelector
from app.models.sample_data import accounts, alliances, kingdoms, players
from app.models.schema import Account, AccountType, Player, Role, next_id
from app.utils.filters import get_id_filter, get_text_filter, set_filter

FILTER_KINGDOM_KEY = "accounts_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "accounts_filter_alliance_id"
FILTER_NAME_KEY = "accounts_filter_name"


def _visible_accounts() -> list[Account]:
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return accounts
    return [a for a in accounts if a.id == role_switcher.current_account_id()]


def _show_filters() -> bool:
    """Filters are hidden only for SchedulerAdmin - see requirements: account
    management/search is an Admin/PowerAdmin/SuperAdmin/User concern, not a
    SchedulerAdmin one. Direct role check (not is_at_least) since SuperAdmin
    should still see filters, not be swept into the SchedulerAdmin exclusion.
    """
    return role_switcher.current_role() != Role.SCHEDULER_ADMIN


def _show_name_filter() -> bool:
    """Name search is an Admin/PowerAdmin/SuperAdmin tool - a plain User only ever
    sees their own single account row, so a search box adds nothing for them.
    is_at_least() already treats SuperAdmin as included alongside the listed roles.
    """
    return role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)


def _show_kingdom_alliance_filter() -> bool:
    """Kingdom/Alliance dropdowns are SuperAdmin-only (per requirements) - regular
    Admin/PowerAdmin already only ever see their own alliance's accounts... except
    Account has no alliance_id of its own (it's derived via Player), and today's
    _visible_accounts() doesn't actually scope Admin/PowerAdmin by alliance yet.
    SuperAdmin is the one role that spans every kingdom/alliance, so it's the one
    that benefits from narrowing by them.
    """
    return role_switcher.current_role() == Role.SUPER_ADMIN


def _players_matching(*, kingdom_id: int | None = None, alliance_id: int | None = None) -> list[Player]:
    rows = players
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    return rows


def _kingdom_ids_from_players(rows: list[Player]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _account_ids_from_players(rows: list[Player]) -> set[int]:
    return {p.account_id for p in rows}


def _reconcile_filters() -> None:
    """Mirrors app/pages/players.py's _reconcile_filters(): clears Kingdom/Alliance
    whenever the other one no longer has matching data, so the two dropdowns stay
    mutually consistent no matter which one you just touched.
    """
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _kingdom_ids_from_players(players))
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, {p.alliance_id for p in players})

    if alliance_id is not None:
        valid = {p.alliance_id for p in _players_matching(kingdom_id=kingdom_id)}
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(_players_matching(alliance_id=alliance_id))
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)


def _clear_account_filters() -> None:
    set_filter(FILTER_KINGDOM_KEY, None)
    set_filter(FILTER_ALLIANCE_KEY, None)
    set_filter(FILTER_NAME_KEY, "")
    account_filters.refresh()
    account_table.refresh()


def _filtered_accounts() -> list[Account]:
    rows = _visible_accounts()

    if _show_kingdom_alliance_filter():
        kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _kingdom_ids_from_players(players))
        alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, {p.alliance_id for p in players})
        if kingdom_id is not None or alliance_id is not None:
            matching_account_ids = _account_ids_from_players(
                _players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id)
            )
            rows = [a for a in rows if a.id in matching_account_ids]

    name = get_text_filter(FILTER_NAME_KEY).strip().lower() if _show_name_filter() else ""
    if name:
        rows = [
            a for a in rows
            if name in a.account_name.lower() or (a.discord_global_name and name in a.discord_global_name.lower())
        ]
    return rows


@ui.page("/accounts")
def accounts_page() -> None:
    ui.page_title("Accounts - Kingshot Scheduler")
    with layout.frame("/accounts"):
        can_manage_others = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Account Management").classes("text-2xl font-bold")
            if can_manage_others:
                ui.button("Add Account", icon="add", on_click=_open_add_account_dialog) \
                    .props("unelevated color=primary")
        if not can_manage_others:
            ui.label("You can view and edit your own account below.").classes("text-grey-6")

        account_filters()
        account_table()


@ui.refreshable
def account_filters() -> None:
    if not _show_filters():
        return

    show_kingdom_alliance = _show_kingdom_alliance_filter()
    show_name = _show_name_filter()
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _kingdom_ids_from_players(players)) if show_kingdom_alliance else None
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, {p.alliance_id for p in players}) if show_kingdom_alliance else None
    name = get_text_filter(FILTER_NAME_KEY) if show_name else ""

    if not show_kingdom_alliance and not show_name:
        return  # nothing left to render for this role (e.g. a plain User)

    # Each dropdown's options come from the *other* active filter, mirroring
    # app/pages/players.py's player_filters() - selecting a Kingdom narrows Alliance
    # options and vice versa, and both dropdowns' displayed *value* stays in sync
    # with what's actually possible given the other's current selection.
    kingdom_option_ids = _kingdom_ids_from_players(_players_matching(alliance_id=alliance_id))
    alliance_option_ids = {p.alliance_id for p in _players_matching(kingdom_id=kingdom_id)}

    with ui.row().classes("w-full items-end gap-2"):
        # Order: Kingdom, Alliance, then Name - Kingdom/Alliance only render for
        # SuperAdmin, so this puts the coarse-to-fine structured filters first.
        kingdom_select = alliance_select = None
        if show_kingdom_alliance:
            kingdom_options = {k.id: k.name for k in kingdoms if k.id in kingdom_option_ids}
            kingdom_select = ui.select(
                kingdom_options, label="Kingdom", value=kingdom_id,
            ).props("outlined dense clearable").classes("w-48")

            alliance_options = {a.id: a.name for a in alliances if a.id in alliance_option_ids}
            alliance_select = ui.select(
                alliance_options, label="Alliance", value=alliance_id,
            ).props("outlined dense clearable").classes("w-48")

        name_input = None
        if show_name:
            name_input = ui.input("Search Account Name", value=name) \
                .props("outlined dense clearable").classes("w-56")

        def _apply_structured_change() -> None:
            _reconcile_filters()
            account_filters.refresh()
            account_table.refresh()

        def on_kingdom_change() -> None:
            set_filter(FILTER_KINGDOM_KEY, kingdom_select.value)
            _apply_structured_change()

        def on_alliance_change() -> None:
            set_filter(FILTER_ALLIANCE_KEY, alliance_select.value)
            _apply_structured_change()

        def on_name_change() -> None:
            set_filter(FILTER_NAME_KEY, name_input.value or "")
            account_table.refresh()  # name search never changes dropdown options

        if name_input is not None:
            name_input.on_value_change(on_name_change)
        if kingdom_select is not None:
            kingdom_select.on_value_change(on_kingdom_change)
        if alliance_select is not None:
            alliance_select.on_value_change(on_alliance_change)

        if kingdom_id is not None or alliance_id is not None or name:
            ui.button("Clear Filters", icon="close", on_click=_clear_account_filters).props("flat dense")


@ui.refreshable
def account_table() -> None:
    can_edit = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)
    show_admin_columns = role_switcher.is_any_admin()
    filtered = _filtered_accounts()

    player_count_by_account: dict[int, int] = {}
    for p in players:
        player_count_by_account[p.account_id] = player_count_by_account.get(p.account_id, 0) + 1

    rows = []
    for a in filtered:
        display_name = f"{a.account_name} ({a.discord_global_name})" if a.discord_global_name else a.account_name
        row = {
            "id": a.id,
            "avatar_url": a.discord_avatar_url,
            "account_name": display_name,
            "player_count": player_count_by_account.get(a.id, 0),
            "time_zone": a.time_zone,
        }
        if show_admin_columns:
            row["account_type"] = a.account_type.value
            row["super_admin"] = "Yes" if a.is_super_admin else ""
        rows.append(row)

    columns = [
        {"name": "avatar_url", "label": "", "field": "avatar_url"},
        {"name": "account_name", "label": "Account", "field": "account_name", "sortable": True},
        {"name": "player_count", "label": "Players", "field": "player_count", "sortable": True},
        {"name": "time_zone", "label": "Time Zone", "field": "time_zone", "sortable": True},
    ]
    if show_admin_columns:
        columns.append({"name": "account_type", "label": "Type", "field": "account_type", "sortable": True})
        columns.append({"name": "super_admin", "label": "SuperAdmin", "field": "super_admin"})

    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")
    # Custom cell: q-avatar with the Discord image if we have one, else a generic icon.
    # ui.table has no Python-level "image column" option, so this is one of the rare
    # legitimate uses of a Quasar template string (nicegui_llms.md > Named Slots).
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
    if can_edit:
        # Plain text, no link styling - matches app/pages/players.py and every other
        # list page, none of which style a column as a fake link either. Row-click-to-
        # edit isn't wired up yet, so there's nothing to visually signal as clickable.
        ui.label("(Admin/PowerAdmin: click a row in the real app to edit or remove an account)") \
            .classes("text-xs text-grey-5")

    if not filtered and _visible_accounts():
        ui.label("No accounts match the current filters.").classes("text-sm text-grey-5")


def _open_add_account_dialog() -> None:
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Account").classes("text-lg font-bold")
        ui.label("Creates a manual account with no players yet - use Add Player afterwards "
                 "to attach it to a Kingdom/Alliance.").classes("text-xs text-grey-6")

        name_input = ui.input("Account Name").props("outlined").classes("w-full")
        tz_selector = TimeZoneSelector()

        def submit() -> None:
            if not name_input.value:
                ui.notify("Account name is required", type="warning")
                return
            if not tz_selector.value:
                ui.notify("Select a time zone", type="warning")
                return
            accounts.append(Account(
                id=next_id(),
                account_type=AccountType.MANUAL_USER,
                account_name=name_input.value,
                time_zone=tz_selector.value,
                create_account_id=role_switcher.current_account_id(),
                update_account_id=role_switcher.current_account_id(),
            ))
            dialog.close()
            # Refresh both: a new account can introduce data the filter dropdowns
            # don't yet reflect (mirrors app/pages/players.py's Add Player handler).
            account_filters.refresh()
            account_table.refresh()
            ui.notify("Account added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add Account", on_click=submit).props("unelevated color=primary")

    dialog.open()
