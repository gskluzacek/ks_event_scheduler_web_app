"""
Player Management.

The "Add Player" dialog implements the Player Joining Alliance flow from
web_app_requirements.md: pick Kingdom -> Alliance -> Verify Guild Membership
(bot-token check) -> only then can Kingshot player details be entered.
"""
from __future__ import annotations

from nicegui import app, ui

from app.auth.discord_guild import MembershipResult, build_guild_avatar_url, verify_guild_membership
from app.components import layout, role_switcher
from app.models.sample_data import accounts, alliances, kingdoms, players, time_slots
from app.models.schema import Account, AccountType, Player, Role, TOWN_CENTER_LEVELS, next_id
from app.utils.filters import get_id_filter, get_text_filter, set_filter

FILTER_KINGDOM_KEY = "players_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "players_filter_alliance_id"
FILTER_ACCOUNT_KEY = "players_filter_account_id"
FILTER_NAME_KEY = "players_filter_name"


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


ACCOUNTS_PAGE_KEY = "players_accounts_page"
EXPANDED_ACCOUNTS_KEY = "players_expanded_account_ids"
ACCOUNTS_PAGE_SIZE = 5


def _player_rows(rows: list[Player], *, show_roles: bool) -> list[dict]:
    """Builds one display-ready dict per player (avatar url, resolved kingdom/alliance
    names, formatted power, etc.) - shared by every player card so the field set/
    formatting is defined exactly once.
    """
    alliance_by_id = {a.id: a for a in alliances}
    kingdom_name_by_id = {k.id: k.name for k in kingdoms}
    account_by_id = {a.id: a for a in accounts}
    slot_count_by_player_id: dict[int, int] = {}
    for slot in time_slots:
        slot_count_by_player_id[slot.player_id] = slot_count_by_player_id.get(slot.player_id, 0) + 1

    result = []
    for p in rows:
        account = account_by_id.get(p.account_id)
        # Guild-specific avatar if the player has one; else the account's global Discord
        # avatar; else None (renders as a generic person icon).
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
            "timeslot_count": slot_count_by_player_id.get(p.id, 0),
            "discord_nickname": p.discord_nickname or "",
        }
        if show_roles:
            row["roles"] = ", ".join(r.value for r in p.roles)
        result.append(row)
    return result


def _get_expanded_account_ids() -> set[int]:
    return set(app.storage.user.get(EXPANDED_ACCOUNTS_KEY, []))


def _get_accounts_page() -> int:
    return app.storage.user.get(ACCOUNTS_PAGE_KEY, 1)


def _render_player_card(row: dict, *, show_roles: bool) -> None:
    """One 'child card' - a player's details laid out so nothing needs a horizontal
    scrollbar: a grid that wraps to the card's width instead of adding columns.
    """
    with ui.card().classes("w-full").props("flat bordered"):
        with ui.row().classes("items-start gap-3 w-full no-wrap"):
            with ui.avatar(size="40px", color="grey-4", text_color="grey-8"):
                if row["avatar_url"]:
                    ui.image(row["avatar_url"]).style("object-fit: cover")
                else:
                    ui.icon("person")
            with ui.column().classes("gap-1 grow"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(row["kingshot_name"]).classes("font-bold")
                    ui.badge(f"TC {row['tc_level']}").props("color=grey-6")
                with ui.grid(columns=3).classes("gap-x-4 gap-y-0 text-sm w-full"):
                    ui.label(f"Kingdom: {row['kingdom']}")
                    ui.label(f"Alliance: {row['alliance']}")
                    ui.label(f"Kingshot ID: {row['kingshot_id']}")
                    ui.label(f"Power: {row['power']}")
                    ui.label(f"Time Slots: {row['timeslot_count']}")
                    ui.label(f"Discord: {row['discord_nickname'] or '—'}")
                    if show_roles:
                        ui.label(f"Roles: {row['roles']}")


def _render_account_card(account: Account, account_rows: list[dict], *, show_roles: bool) -> None:
    """The 'parent card': account-level header (name, time zone, Discord username,
    player count) plus a disclosure toggle that shows/hides a scrollable stack of
    that account's player cards underneath - see Greg's mockup.
    """
    expanded = account.id in _get_expanded_account_ids()

    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.row().classes("items-center gap-4"):
                ui.icon("account_circle").classes("text-2xl")
                ui.label(account.account_name).classes("font-bold text-lg")
                ui.label(account.time_zone).classes("text-sm text-grey-6")
                if account.account_type == AccountType.DISCORD_USER:
                    ui.label(f"@{account.discord_username}").classes("text-sm text-grey-6")
                else:
                    ui.label("Manual account").classes("text-sm text-grey-6")
                ui.badge(str(len(account_rows))).props("color=primary")
                ui.label("player" + ("s" if len(account_rows) != 1 else "")).classes("text-sm text-grey-6")
            toggle_button = ui.button(icon="expand_less" if expanded else "expand_more").props("flat round dense")

        with ui.scroll_area().classes("h-72 w-full") as child_area:
            with ui.column().classes("w-full gap-2"):
                for row in account_rows:
                    _render_player_card(row, show_roles=show_roles)
        child_area.set_visibility(expanded)

        def toggle(acct_id=account.id, area=child_area, btn=toggle_button) -> None:
            ids = _get_expanded_account_ids()
            now_expanded = acct_id not in ids
            if now_expanded:
                ids.add(acct_id)
            else:
                ids.discard(acct_id)
            app.storage.user[EXPANDED_ACCOUNTS_KEY] = list(ids)
            area.set_visibility(now_expanded)
            btn.props(f"icon={'expand_less' if now_expanded else 'expand_more'}")

        toggle_button.on_click(toggle)


@ui.refreshable
def player_table() -> None:
    filtered = _filtered_players()
    # Roles are about role *management*, a PowerAdmin-only capability (see
    # web_app_requirements.md > Account Management #3) - hidden for other roles.
    show_roles = role_switcher.is_at_least(Role.POWER_ADMIN)

    if not filtered:
        if _visible_players():
            ui.label("No players match the current filters.").classes("text-sm text-grey-5")
        return

    account_by_id = {a.id: a for a in accounts}
    rows_by_account: dict[int, list[dict]] = {}
    for row in _player_rows(filtered, show_roles=show_roles):
        player = next(p for p in filtered if p.id == row["id"])
        rows_by_account.setdefault(player.account_id, []).append(row)

    account_ids = sorted(rows_by_account, key=lambda aid: account_by_id[aid].account_name.lower())

    # Paginate the account (parent) cards - simpler and more predictable than a
    # fixed-height outer scroll panel, and works for 1 account or 1000 alike.
    total_pages = max(1, -(-len(account_ids) // ACCOUNTS_PAGE_SIZE))  # ceil division
    page = min(max(1, _get_accounts_page()), total_pages)
    start = (page - 1) * ACCOUNTS_PAGE_SIZE
    page_account_ids = account_ids[start:start + ACCOUNTS_PAGE_SIZE]

    for account_id in page_account_ids:
        _render_account_card(account_by_id[account_id], rows_by_account[account_id], show_roles=show_roles)

    if total_pages > 1:
        def on_page_change(e) -> None:
            app.storage.user[ACCOUNTS_PAGE_KEY] = e.value
            player_table.refresh()

        with ui.row().classes("w-full justify-center"):
            ui.pagination(min=1, max=total_pages, value=page, direction_links=True, on_change=on_page_change)


def _set_enabled(element, enabled: bool) -> None:
    """Toggle a Quasar 'disable' prop - used for buttons that depend on prior
    steps being completed (e.g. Verify Guild Membership, then Add Player).
    """
    if enabled:
        element.props(remove="disable")
    else:
        element.props("disable")


def _account_alliance_summary(account_id: int) -> str:
    """'Kingdom / Alliance' for each of this account's existing players, used only to
    give an admin picking an account some context - a brand-new account with no
    players yet simply shows nothing here.
    """
    alliance_by_id = {a.id: a for a in alliances}
    kingdom_name_by_id = {k.id: k.name for k in kingdoms}
    names = sorted({
        f"{kingdom_name_by_id.get(alliance_by_id[p.alliance_id].kingdom_id, '?')} / {alliance_by_id[p.alliance_id].name}"
        for p in players if p.account_id == account_id and p.alliance_id in alliance_by_id
    })
    return ", ".join(names) if names else "No players yet"


def _open_add_player_dialog() -> None:
    is_admin_flow = role_switcher.is_any_admin()

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        step1_container = ui.column().classes("w-full gap-2")
        step2_container = ui.column().classes("w-full gap-2")
        step2_container.set_visibility(not is_admin_flow)

        if is_admin_flow:
            _build_account_picker_step(dialog, step1_container, step2_container)
        else:
            own_account = next(a for a in accounts if a.id == role_switcher.current_account_id())
            with step2_container:
                _build_player_details_step(dialog, own_account)

    dialog.open()


def _build_account_picker_step(dialog, step1_container, step2_container) -> None:
    """Step 1 of the admin "Add Player" flow: search for and select which account
    the new player will belong to, before touching alliance/guild verification at
    all (per Greg's request - the account must be determined first).
    """
    selected_account_id: dict[str, int | None] = {"value": None}

    with step1_container:
        ui.label("Select Account").classes("text-lg font-bold")
        search_input = ui.input("Search Account Name").props("outlined dense clearable autofocus").classes("w-full")
        results_column = ui.column().classes("w-full gap-1 max-h-96 overflow-auto")

        def render_results() -> None:
            results_column.clear()
            query = (search_input.value or "").strip().lower()
            matches = [a for a in accounts if not query or query in a.account_name.lower()]
            with results_column:
                if not matches:
                    ui.label("No matching accounts.").classes("text-sm text-grey-5")
                for acc in matches:
                    is_selected = selected_account_id["value"] == acc.id
                    with ui.card().classes(
                        "w-full cursor-pointer" + (" bg-blue-1" if is_selected else "")
                    ).props("flat bordered").on("click", lambda a=acc: select_account(a)):
                        with ui.row().classes("items-center gap-3 w-full"):
                            with ui.avatar(size="32px", color="grey-4", text_color="grey-8"):
                                if acc.discord_avatar_url:
                                    ui.image(acc.discord_avatar_url)
                                else:
                                    ui.icon("person")
                            with ui.column().classes("gap-0"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(acc.account_name).classes("font-bold")
                                    ui.badge(acc.account_type.value).props("color=grey-6")
                                if acc.account_type == AccountType.DISCORD_USER:
                                    ui.label(
                                        f"{acc.discord_global_name or ''} (@{acc.discord_username})"
                                    ).classes("text-xs text-grey-6")
                                ui.label(_account_alliance_summary(acc.id)).classes("text-xs text-grey-6")

        def select_account(acc: Account) -> None:
            selected_account_id["value"] = acc.id
            render_results()
            _set_enabled(continue_button, True)

        search_input.on_value_change(render_results)
        render_results()

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            continue_button = ui.button("Continue", icon="arrow_forward").props("unelevated color=primary")
        _set_enabled(continue_button, False)

        def on_continue() -> None:
            account = next(a for a in accounts if a.id == selected_account_id["value"])
            step1_container.set_visibility(False)
            step2_container.set_visibility(True)
            with step2_container:
                _build_player_details_step(dialog, account)

        continue_button.on_click(on_continue)


def _build_player_details_step(dialog, account: Account) -> None:
    """Step 2 (and the only step, for non-admins): pick the alliance to join, verify
    guild membership - unless `account` is a manual (non-Discord) account, in which
    case verification is skipped entirely - then enter the Kingshot player details.
    """
    is_manual_account = account.account_type == AccountType.MANUAL_USER
    verified_alliance_id: dict[str, int | None] = {"value": None}
    verified_nickname: dict[str, str | None] = {"value": None}
    verified_avatar_hash: dict[str, str | None] = {"value": None}

    ui.label("Add Player").classes("text-lg font-bold")
    if is_manual_account:
        ui.label(f"Account: {account.account_name} (manual - guild check skipped)").classes("text-sm text-grey-6")
    else:
        ui.label(f"Account: {account.account_name}").classes("text-sm text-grey-6")

    kingdom_select = ui.select(
        {k.id: k.name for k in kingdoms}, label="Kingdom"
    ).props("outlined").classes("w-full")
    alliance_select = ui.select({}, label="Alliance").props("outlined").classes("w-full")
    guild_label = ui.label().classes("text-sm text-grey-6")
    verify_status = ui.label().classes("text-sm")

    def _sync_buttons() -> None:
        if not is_manual_account:
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
        details_column.set_visibility(False)
        _sync_buttons()

    def on_alliance_change() -> None:
        alliance = next((a for a in alliances if a.id == alliance_select.value), None)
        verified_alliance_id["value"] = None
        verified_avatar_hash["value"] = None
        if is_manual_account:
            # No Discord guild to check membership against - the alliance choice alone
            # is enough to set the player's alliance_id, so unlock the details form.
            guild_label.set_text("")
            if alliance:
                verified_alliance_id["value"] = alliance.id
                verify_status.classes(remove="text-negative", add="text-positive")
                verify_status.set_text("✓ Manual account - no guild check needed")
                details_column.set_visibility(True)
            else:
                verify_status.set_text("")
                details_column.set_visibility(False)
        else:
            guild_label.set_text(f"Discord guild: {alliance.discord_guild_name}" if alliance else "")
            verify_status.set_text("")
            details_column.set_visibility(False)
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
            verify_status.set_text("✗ Not a member of this guild.")
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

    if not is_manual_account:
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
        # account's global avatar, then a generic icon, if this is unset. Manual
        # accounts have no Discord identity at all, so this is always None for them.
        guild_avatar_url = None
        if not is_manual_account:
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

    _sync_buttons()  # buttons start disabled - nothing's selected/verified yet
