"""
Player Management.

The "Add Player" dialog implements the Player Joining Alliance flow from
web_app_requirements.md: pick Kingdom -> Alliance -> Verify Guild Membership
(bot-token check) -> only then can Kingshot player details be entered.
"""
from __future__ import annotations

from nicegui import ui

from app.auth.discord_guild import MembershipResult, build_guild_avatar_url, verify_guild_membership
from app.components import layout, role_switcher
from app.models.sample_data import accounts, alliances, kingdoms, players
from app.models.schema import Player, Role, TOWN_CENTER_LEVELS, next_id
from app.utils.filters import get_id_filter, get_sort_state, get_text_filter, set_filter, set_sort_state

FILTER_KINGDOM_KEY = "players_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "players_filter_alliance_id"
FILTER_ACCOUNT_KEY = "players_filter_account_id"
FILTER_NAME_KEY = "players_filter_name"
SORT_BY_KEY = "players_sort_by"
SORT_DESC_KEY = "players_sort_desc"


def _visible_players() -> list[Player]:
    role = role_switcher.current_role()
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return players
    account_id = role_switcher.current_account_id()
    return [p for p in players if p.account_id == account_id]


def _visible_alliance_ids() -> set[int]:
    """Alliance IDs actually present among the players this viewer can see -
    used to keep the Alliance filter from offering choices with zero results.
    """
    return {p.alliance_id for p in _visible_players()}


def _visible_kingdom_ids() -> set[int]:
    """Same idea as _visible_alliance_ids(), one level up: only kingdoms that
    have at least one visible player in one of their alliances.
    """
    alliance_ids = _visible_alliance_ids()
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _visible_account_ids() -> set[int]:
    return {p.account_id for p in _visible_players()}


def _visible_players_matching(
    *, kingdom_id: int | None = None, alliance_id: int | None = None, account_id: int | None = None,
) -> list[Player]:
    """Visible players narrowed by whichever of kingdom/alliance/account are given.
    Used to compute each filter dropdown's options from the *other* active filters, so
    Kingdom/Alliance/Account stay mutually consistent - not just the one-way
    Kingdom -> Alliance cascade this used to have.
    """
    rows = _visible_players()
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    if account_id is not None:
        rows = [p for p in rows if p.account_id == account_id]
    return rows


def _kingdom_ids_from_players(rows: list[Player]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _filtered_players() -> list[Player]:
    rows = _visible_players()
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    name = get_text_filter(FILTER_NAME_KEY).strip().lower()

    if kingdom_id is not None:
        alliance_ids = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    # The Account filter only exists (and only applies) for admin-type viewers - a
    # regular user's visible players already belong to a single account.
    if role_switcher.is_any_admin():
        account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids())
        if account_id is not None:
            rows = [p for p in rows if p.account_id == account_id]
    if name:
        rows = [p for p in rows if name in p.kingshot_name.lower()]
    return rows


@ui.page("/players")
def players_page() -> None:
    ui.page_title("Players - Kingshot Scheduler")
    with layout.frame("/players"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Player Management").classes("text-2xl font-bold")
            ui.button("Add Player", icon="add", on_click=lambda: _open_add_player_dialog()) \
                .props("unelevated color=primary")

        player_filters()
        player_table()


@ui.refreshable
def player_filters() -> None:
    show_account = role_switcher.is_any_admin()
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids()) if show_account else None
    name = get_text_filter(FILTER_NAME_KEY)

    # Each dropdown's options come from the *other* active structured filters, so
    # selecting any one of Kingdom/Alliance/Account narrows the others - in every
    # direction, not just Kingdom -> Alliance. Name search is deliberately left out of
    # this so these options don't shift under you while typing (see note below).
    kingdom_option_ids = _kingdom_ids_from_players(
        _visible_players_matching(alliance_id=alliance_id, account_id=account_id)
    )
    alliance_option_ids = {
        p.alliance_id for p in _visible_players_matching(kingdom_id=kingdom_id, account_id=account_id)
    }
    account_option_ids = {
        p.account_id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id)
    } if show_account else set()

    with ui.row().classes("w-full items-end gap-2"):
        # Options are restricted to what's actually in this viewer's data (not every
        # kingdom/alliance/account that exists) - no point offering a choice with zero
        # results. This is deliberately based on the *unfiltered* visible set for name
        # search, so options don't shift under you while typing - only the structured
        # Kingdom/Alliance/Account filters narrow each other.
        kingdom_options = {k.id: k.name for k in kingdoms if k.id in kingdom_option_ids}
        kingdom_select = ui.select(
            kingdom_options, label="Kingdom", value=kingdom_id,
        ).props("outlined dense clearable").classes("w-48")

        alliance_options = {a.id: a.name for a in alliances if a.id in alliance_option_ids}
        alliance_select = ui.select(
            alliance_options, label="Alliance", value=alliance_id,
        ).props("outlined dense clearable").classes("w-48")

        account_select = None
        if show_account:
            account_options = {
                acc.id: acc.account_name for acc in accounts if acc.id in account_option_ids
            }
            account_select = ui.select(
                account_options, label="Account", value=account_id,
            ).props("outlined dense clearable").classes("w-44")

        name_input = ui.input("Search Kingshot Name", value=name) \
            .props("outlined dense clearable").classes("w-56")

        def _apply_structured_change() -> None:
            """Shared tail for a Kingdom/Alliance/Account change: clear any other
            selection that's no longer consistent with it, then refresh the filter
            row (so options + values catch up) and the table.
            """
            _reconcile_filters()
            player_filters.refresh()
            player_table.refresh()

        def on_kingdom_change() -> None:
            set_filter(FILTER_KINGDOM_KEY, kingdom_select.value)
            _apply_structured_change()

        def on_alliance_change() -> None:
            set_filter(FILTER_ALLIANCE_KEY, alliance_select.value)
            _apply_structured_change()

        def on_account_change() -> None:
            set_filter(FILTER_ACCOUNT_KEY, account_select.value)
            _apply_structured_change()

        def on_name_change() -> None:
            set_filter(FILTER_NAME_KEY, name_input.value or "")
            player_table.refresh()  # name search never changes dropdown options

        kingdom_select.on_value_change(on_kingdom_change)
        alliance_select.on_value_change(on_alliance_change)
        if account_select is not None:
            account_select.on_value_change(on_account_change)
        name_input.on_value_change(on_name_change)

        if kingdom_id is not None or alliance_id is not None or account_id is not None or name:
            ui.button("Clear Filters", icon="close", on_click=_clear_player_filters).props("flat dense")


def _reconcile_filters() -> None:
    """Clears any structured filter (Kingdom/Alliance/Account) whose stored value no
    longer has matching data given the other two - called after any of them changes,
    so the three stay mutually consistent regardless of which one you just touched.
    """
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    account_id = get_id_filter(FILTER_ACCOUNT_KEY, _visible_account_ids()) if role_switcher.is_any_admin() else None

    if alliance_id is not None:
        valid = {p.alliance_id for p in _visible_players_matching(kingdom_id=kingdom_id, account_id=account_id)}
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(_visible_players_matching(alliance_id=alliance_id, account_id=account_id))
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)
            kingdom_id = None
    if account_id is not None:
        valid = {p.account_id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id)}
        if account_id not in valid:
            set_filter(FILTER_ACCOUNT_KEY, None)


def _clear_player_filters() -> None:
    set_filter(FILTER_KINGDOM_KEY, None)
    set_filter(FILTER_ALLIANCE_KEY, None)
    set_filter(FILTER_ACCOUNT_KEY, None)
    set_filter(FILTER_NAME_KEY, "")
    player_filters.refresh()
    player_table.refresh()


@ui.refreshable
def player_table() -> None:
    filtered = _filtered_players()
    show_account = role_switcher.is_any_admin()
    # Roles column is about role *management*, which is a PowerAdmin-only capability
    # (see web_app_requirements.md > Account Management #3) - so it's hidden for the
    # more common viewer roles (User, Admin, SchedulerAdmin) rather than shown to all.
    show_roles = role_switcher.is_at_least(Role.POWER_ADMIN)

    # Precomputed once per render rather than re-scanning `alliances`/`accounts` per row.
    alliance_by_id = {a.id: a for a in alliances}
    kingdom_name_by_id = {k.id: k.name for k in kingdoms}
    account_name_by_id = {a.id: a.account_name for a in accounts}
    account_by_id = {a.id: a for a in accounts}

    rows = []
    for p in filtered:
        account = account_by_id.get(p.account_id)
        # Guild-specific avatar if the player has one; else the account's global Discord
        # avatar; else None (renders as a generic person icon - see the table slot below).
        avatar_url = p.discord_guild_avatar_url or (account.discord_avatar_url if account else None)
        row = {
            "id": p.id,
            "avatar_url": avatar_url,
            "kingdom": kingdom_name_by_id.get(
                alliance_by_id[p.alliance_id].kingdom_id if p.alliance_id in alliance_by_id else None, "?"
            ),
            "alliance": alliance_by_id[p.alliance_id].name if p.alliance_id in alliance_by_id else "?",
            "kingshot_id": p.kingshot_id,
            "kingshot_name": p.kingshot_name,
            "tc_level": p.town_center_level,
            "power": f"{p.power:,}",
            "discord_nickname": p.discord_nickname or "",
        }
        if show_account:
            row["account"] = account_name_by_id.get(p.account_id, "?")
        if show_roles:
            row["roles"] = ", ".join(r.value for r in p.roles)
        rows.append(row)

    columns = [
        {"name": "avatar_url", "label": "", "field": "avatar_url"},
        {"name": "kingdom", "label": "Kingdom", "field": "kingdom", "sortable": True},
        {"name": "alliance", "label": "Alliance", "field": "alliance", "sortable": True},
    ]
    if show_account:
        columns.append({"name": "account", "label": "Account", "field": "account", "sortable": True})
    columns += [
        {"name": "kingshot_id", "label": "Kingshot ID", "field": "kingshot_id"},
        {"name": "kingshot_name", "label": "Kingshot Name", "field": "kingshot_name", "sortable": True},
        {"name": "tc_level", "label": "TC Level", "field": "tc_level", "sortable": True},
        {"name": "power", "label": "Power", "field": "power", "sortable": True},
        {"name": "discord_nickname", "label": "Discord Nickname", "field": "discord_nickname", "sortable": True},
    ]
    if show_roles:
        columns.append({"name": "roles", "label": "Roles", "field": "roles"})

    sort_by, sort_desc = get_sort_state(SORT_BY_KEY, SORT_DESC_KEY)
    # rowsPerPage: 0 = show every row, no pagination bar - we only use this prop to
    # carry sort state, not to actually paginate.
    table = ui.table(
        columns=columns, rows=rows, row_key="id",
        pagination={"sortBy": sort_by, "descending": sort_desc, "rowsPerPage": 0},
    ).classes("w-full").props("flat bordered")
    # Custom cell: q-avatar with the guild/global Discord image if we have one, else a
    # generic icon. ui.table has no Python-level "image column" option, so this is one of
    # the rare legitimate uses of a Quasar template string (nicegui_llms.md > Named Slots).
    table.add_slot(
        "body-cell-avatar_url",
        '''
        <q-td :props="props">
            <q-avatar size="28px" color="grey-4" text-color="grey-8" icon="person">
                <img v-if="props.value" :src="props.value" />
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

    if not filtered and _visible_players():
        ui.label("No players match the current filters.").classes("text-sm text-grey-5")


def _set_enabled(element, enabled: bool) -> None:
    """Toggle a Quasar 'disable' prop - used for buttons that depend on prior
    steps being completed (e.g. Verify Guild Membership, then Add Player).
    """
    if enabled:
        element.props(remove="disable")
    else:
        element.props("disable")


def _open_add_player_dialog() -> None:
    account = next(a for a in accounts if a.id == role_switcher.current_account_id())
    verified_alliance_id: dict[str, int | None] = {"value": None}
    verified_nickname: dict[str, str | None] = {"value": None}
    verified_avatar_hash: dict[str, str | None] = {"value": None}

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Player").classes("text-lg font-bold")

        kingdom_select = ui.select(
            {k.id: k.name for k in kingdoms}, label="Kingdom"
        ).props("outlined").classes("w-full")
        alliance_select = ui.select({}, label="Alliance").props("outlined").classes("w-full")
        guild_label = ui.label().classes("text-sm text-grey-6")
        verify_status = ui.label().classes("text-sm")

        def _sync_buttons() -> None:
            _set_enabled(verify_button, bool(kingdom_select.value) and bool(alliance_select.value))
            _set_enabled(add_button, bool(verified_alliance_id["value"]))

        def on_kingdom_change() -> None:
            options = {a.id: a.name for a in alliances if a.kingdom_id == kingdom_select.value}
            alliance_select.set_options(options)
            alliance_select.value = None
            guild_label.set_text("")
            verify_status.set_text("")
            verified_alliance_id["value"] = None
            verified_avatar_hash["value"] = None
            _sync_buttons()

        def on_alliance_change() -> None:
            alliance = next((a for a in alliances if a.id == alliance_select.value), None)
            guild_label.set_text(f"Discord guild: {alliance.discord_guild_name}" if alliance else "")
            verify_status.set_text("")
            verified_alliance_id["value"] = None
            verified_avatar_hash["value"] = None
            _sync_buttons()

        kingdom_select.on_value_change(on_kingdom_change)
        alliance_select.on_value_change(on_alliance_change)

        async def do_verify() -> None:
            alliance = next((a for a in alliances if a.id == alliance_select.value), None)
            if not alliance:
                ui.notify("Select an alliance first", type="warning")
                return
            verify_status.set_text("Checking membership…")
            check = await verify_guild_membership(alliance.discord_guild_id, account.discord_user_id)
            if check.result == MembershipResult.VERIFIED:
                verified_alliance_id["value"] = alliance.id
                verified_nickname["value"] = check.nickname
                verified_avatar_hash["value"] = check.avatar_hash
                verify_status.classes(remove="text-negative", add="text-positive")
                verify_status.set_text(f"✓ Verified{f' — nick: {check.nickname}' if check.nickname else ''}")
                details_column.set_visibility(True)
            elif check.result == MembershipResult.NOT_A_MEMBER:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ You are not a member of this guild.")
            elif check.result == MembershipResult.BOT_FORBIDDEN:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ Bot credentials are invalid (403).")
            elif check.result == MembershipResult.SERVER_ERROR:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ Discord returned a server error — bot may have been removed.")
            else:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text(f"✗ Unexpected error: {check.detail}")
            _sync_buttons()

        verify_button = ui.button("Verify Guild Membership", icon="verified_user", on_click=do_verify) \
            .props("outlined")

        with ui.column().classes("w-full gap-2") as details_column:
            kingshot_id = ui.input("Kingshot ID").props("outlined").classes("w-full")
            kingshot_name = ui.input("Kingshot Name").props("outlined").classes("w-full")
            power = ui.number("Power", min=0).props("outlined").classes("w-full")
            tc_level = ui.select(TOWN_CENTER_LEVELS, label="Town Center Level").props("outlined").classes("w-full")
        details_column.set_visibility(False)

        def submit() -> None:
            if not verified_alliance_id["value"]:
                ui.notify("Verify guild membership first", type="warning")
                return
            alliance = next(a for a in alliances if a.id == verified_alliance_id["value"])
            # Stores only the guild-specific avatar, if the member actually set one for
            # this server - may be None. Display code (player_table()) falls back to the
            # account's global avatar, then a generic icon, if this is unset.
            guild_avatar_url = build_guild_avatar_url(
                alliance.discord_guild_id, account.discord_user_id, verified_avatar_hash["value"]
            )
            players.append(Player(
                id=next_id(),
                account_id=account.id,
                alliance_id=verified_alliance_id["value"],
                kingshot_id=kingshot_id.value or "",
                kingshot_name=kingshot_name.value or "",
                discord_nickname=verified_nickname["value"],
                power=int(power.value or 0),
                town_center_level=tc_level.value or TOWN_CENTER_LEVELS[0],
                roles=[Role.USER],
                discord_guild_avatar_url=guild_avatar_url,
            ))
            dialog.close()
            # Refresh both: a new player can introduce a kingdom/alliance/account that
            # wasn't in the data-driven filter dropdowns before (see player_filters()).
            player_filters.refresh()
            player_table.refresh()
            ui.notify("Player added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            add_button = ui.button("Add Player", on_click=submit).props("unelevated color=primary")

        _sync_buttons()  # both buttons start disabled - nothing's selected/verified yet

    dialog.open()
