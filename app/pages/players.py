"""
Account + Player Management (merged - see account_player.py for the shared
visibility/edit rules this page is built on).

The page is account-first: every visible account gets a card (even one with
zero players, per Greg's decision - see _render_account_card()), and each
account's players are nested underneath, filtered to what this viewer is
allowed to see inside it. This replaced two separate pages/tables because
their card content overlapped heavily - see account_player.py's module
docstring.

The "Add Player" dialog implements the Player Joining Alliance flow from
web_app_requirements.md: pick Kingdom -> Alliance -> Verify Guild Membership
(bot-token check) -> only then can Kingshot player details be entered. It's
launched directly from an account card now (no separate account-picker step -
the account is already known from which card you clicked).
"""
from __future__ import annotations

from datetime import datetime

from nicegui import app, ui

from app.auth.discord_guild import MembershipResult, build_guild_avatar_url, verify_guild_membership
from app.components import layout, role_switcher
from app.models.sample_data import accounts, alliances, kingdoms, players, time_slots
from app.models.schema import Account, AccountType, Player, Role, TOWN_CENTER_LEVELS, next_id
from app.pages.account_player import (
    _admin_alliance_ids,
    _can_edit_account,
    _format_dt,
    _render_copyable_field,
    _render_field,
    _resolve_account_name,
    _set_enabled,
    _visible_accounts,
)
from app.pages.accounts import _open_add_account_dialog, _open_edit_account_dialog, _open_view_account_dialog
from app.utils.filters import get_id_filter, get_text_filter, set_filter

FILTER_KINGDOM_KEY = "players_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "players_filter_alliance_id"
FILTER_ACCOUNT_NAME_KEY = "players_filter_account_name"
FILTER_NAME_KEY = "players_filter_name"

ACCOUNTS_PAGE_KEY = "players_accounts_page"
EXPANDED_ACCOUNTS_KEY = "players_expanded_account_ids"
ACCOUNTS_PAGE_SIZE = 5


def _visible_players() -> list[Player]:
    """Player-level visibility, layered on top of account-level visibility
    (account_player._visible_accounts()):

    - SuperAdmin: every player, no restriction.
    - Admin/PowerAdmin: players in alliances *they themselves* belong to (via
      _admin_alliance_ids()), across every account - not just their own. They
      can see that other accounts exist (_visible_accounts()), just not every
      player inside them.
    - User/SchedulerAdmin: only their own account's players.
    """
    if role_switcher.current_role() == Role.SUPER_ADMIN:
        return players
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        alliance_ids = _admin_alliance_ids()
        return [p for p in players if p.alliance_id in alliance_ids]
    account_id = role_switcher.current_account_id()
    return [p for p in players if p.account_id == account_id]


def _can_edit_player(player: Player) -> bool:
    """Everyone can edit their own player (per requirements: "All users ...
    view, edit and delete their players"); Admin/PowerAdmin can also edit
    others within their alliance scope, since that's all they can see
    (_visible_players()). is_at_least() already folds SuperAdmin in.
    """
    return player.account_id == role_switcher.current_account_id() or role_switcher.is_at_least(
        Role.ADMIN, Role.POWER_ADMIN
    )


def _visible_alliance_ids() -> set[int]:
    """Alliance IDs actually present among the players this viewer can see -
    used to keep the Alliance filter from offering choices with zero results.
    """
    return {p.alliance_id for p in _visible_players()}


def _kingdom_ids_from_players(rows: list[Player]) -> set[int]:
    alliance_ids = {p.alliance_id for p in rows}
    return {a.kingdom_id for a in alliances if a.id in alliance_ids}


def _visible_kingdom_ids() -> set[int]:
    """Same idea as _visible_alliance_ids(), one level up: only kingdoms that
    have at least one visible player in one of their alliances.
    """
    return _kingdom_ids_from_players(_visible_players())


def _visible_players_matching(*, kingdom_id: int | None = None, alliance_id: int | None = None) -> list[Player]:
    """Visible players narrowed by whichever of kingdom/alliance are given.
    Used to compute each filter dropdown's options from the *other* active
    filter, so Kingdom/Alliance stay mutually consistent no matter which one
    you touch first.
    """
    rows = _visible_players()
    if kingdom_id is not None:
        alliance_ids_in_kingdom = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids_in_kingdom]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    return rows


def _reconcile_filters() -> None:
    """Clears Kingdom/Alliance whenever the other one no longer has matching
    data, so the two dropdowns stay mutually consistent no matter which one
    you just touched.
    """
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())

    if alliance_id is not None:
        valid = {p.alliance_id for p in _visible_players_matching(kingdom_id=kingdom_id)}
        if alliance_id not in valid:
            set_filter(FILTER_ALLIANCE_KEY, None)
            alliance_id = None
    if kingdom_id is not None:
        valid = _kingdom_ids_from_players(_visible_players_matching(alliance_id=alliance_id))
        if kingdom_id not in valid:
            set_filter(FILTER_KINGDOM_KEY, None)


def _clear_player_filters() -> None:
    set_filter(FILTER_KINGDOM_KEY, None)
    set_filter(FILTER_ALLIANCE_KEY, None)
    set_filter(FILTER_ACCOUNT_NAME_KEY, "")
    set_filter(FILTER_NAME_KEY, "")
    player_filters.refresh()
    player_table.refresh()


def _filtered_accounts() -> list[Account]:
    """Accounts visible to this viewer (account_player._visible_accounts()),
    narrowed by the Kingdom/Alliance filters (via each account's *visible*
    players - so Admin/PowerAdmin can't use these to find alliances outside
    their own scope) and by the Account Name text filter.

    An account with zero visible players is only included when no Kingdom/
    Alliance filter is active - it has no alliance for those filters to match
    against, so filtering by either necessarily excludes it (see Greg's
    decision on this).
    """
    rows = _visible_accounts()

    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    if kingdom_id is not None or alliance_id is not None:
        matching_account_ids = {
            p.account_id for p in _visible_players_matching(kingdom_id=kingdom_id, alliance_id=alliance_id)
        }
        rows = [a for a in rows if a.id in matching_account_ids]

    account_name = get_text_filter(FILTER_ACCOUNT_NAME_KEY).strip().lower()
    if account_name:
        rows = [
            a for a in rows
            if account_name in a.account_name.lower()
            or (a.discord_global_name and account_name in a.discord_global_name.lower())
        ]
    return rows


def _account_players(account_id: int) -> list[Player]:
    """This viewer's visible players belonging to `account_id`, further
    narrowed by the active Kingdom/Alliance/Kingshot-Name filters - i.e. which
    of that account's players actually show up inside its (possibly expanded)
    card.
    """
    rows = [p for p in _visible_players() if p.account_id == account_id]

    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    if kingdom_id is not None:
        alliance_ids = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]

    name = get_text_filter(FILTER_NAME_KEY).strip().lower()
    if name:
        rows = [p for p in rows if name in p.kingshot_name.lower()]
    return rows


@ui.page("/players")
def players_page() -> None:
    ui.page_title("Accounts & Players - Kingshot Scheduler")
    with layout.frame("/players"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Account & Player Management").classes("text-2xl font-bold")
            if role_switcher.current_role() == Role.SUPER_ADMIN:
                ui.button(
                    "Add Account", icon="add",
                    on_click=lambda: _open_add_account_dialog(
                        on_added=lambda: (player_filters.refresh(), player_table.refresh())
                    ),
                ).props("unelevated color=primary")

        player_filters()
        player_table()


@ui.refreshable
def player_filters() -> None:
    show_account_name = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, _visible_kingdom_ids())
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, _visible_alliance_ids())
    account_name = get_text_filter(FILTER_ACCOUNT_NAME_KEY) if show_account_name else ""
    name = get_text_filter(FILTER_NAME_KEY)

    # Each dropdown's options come from the *other* active structured filter, so
    # selecting either of Kingdom/Alliance narrows the other in both directions.
    # Name search is deliberately left out of this so these options don't shift
    # under you while typing.
    kingdom_option_ids = _kingdom_ids_from_players(_visible_players_matching(alliance_id=alliance_id))
    alliance_option_ids = {p.alliance_id for p in _visible_players_matching(kingdom_id=kingdom_id)}

    with ui.row().classes("w-full items-end gap-2"):
        # Order: Kingdom, Alliance, Account Name, Kingshot Name - coarse-to-fine.
        kingdom_options = {k.id: k.name for k in kingdoms if k.id in kingdom_option_ids}
        kingdom_select = ui.select(
            kingdom_options, label="Kingdom", value=kingdom_id,
        ).props("outlined dense clearable").classes("w-48")

        alliance_options = {a.id: a.name for a in alliances if a.id in alliance_option_ids}
        alliance_select = ui.select(
            alliance_options, label="Alliance", value=alliance_id,
        ).props("outlined dense clearable").classes("w-48")

        account_name_input = None
        if show_account_name:
            account_name_input = ui.input("Search Account Name", value=account_name) \
                .props("outlined dense clearable").classes("w-56")

        name_input = ui.input("Search Kingshot Name", value=name) \
            .props("outlined dense clearable").classes("w-56")

        def _apply_structured_change() -> None:
            """Shared tail for a Kingdom/Alliance change: clear any other
            selection that's no longer consistent with it, then refresh the
            filter row (so options + values catch up) and the table.
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

        def on_account_name_change() -> None:
            set_filter(FILTER_ACCOUNT_NAME_KEY, account_name_input.value or "")
            player_table.refresh()  # text search never changes dropdown options

        def on_name_change() -> None:
            set_filter(FILTER_NAME_KEY, name_input.value or "")
            player_table.refresh()

        kingdom_select.on_value_change(on_kingdom_change)
        alliance_select.on_value_change(on_alliance_change)
        if account_name_input is not None:
            account_name_input.on_value_change(on_account_name_change)
        name_input.on_value_change(on_name_change)

        if kingdom_id is not None or alliance_id is not None or account_name or name:
            ui.button("Clear Filters", icon="close", on_click=_clear_player_filters).props("flat dense")


def _player_rows(rows: list[Player], *, show_roles: bool) -> list[dict]:
    """Builds one display-ready dict per player (avatar url, resolved kingdom/
    alliance names, formatted power, etc.) - shared by every player card so
    the field set/formatting is defined exactly once.
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


def _render_player_card(player: Player, row: dict, *, show_roles: bool) -> None:
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
            with ui.row().classes("gap-1"):
                ui.button("View", icon="visibility", on_click=lambda pl=player: _open_view_player_dialog(pl)) \
                    .props("flat dense no-caps")
                if _can_edit_player(player):
                    ui.button("Edit", icon="edit", on_click=lambda pl=player: _open_edit_player_dialog(pl)) \
                        .props("flat dense no-caps color=primary")


def _render_account_card(account: Account, account_rows: list[tuple[Player, dict]], *, show_roles: bool) -> None:
    """The 'parent card': account-level header (name, time zone, Discord username,
    player count), View/Edit/Add Player actions, and a disclosure toggle that
    shows/hides a scrollable stack of that account's player cards underneath.

    An account with zero (visible/matching) players still gets a card - its
    toggle is disabled with a tooltip instead of an empty scroll area, per
    Greg's decision, so a brand-new account isn't invisible until a player is
    attached.
    """
    has_players = bool(account_rows)
    expanded = has_players and account.id in _get_expanded_account_ids()

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
            with ui.row().classes("items-center gap-1"):
                ui.button("View", icon="visibility", on_click=lambda a=account: _open_view_account_dialog(a)) \
                    .props("flat dense no-caps")
                if _can_edit_account(account.id):
                    ui.button(
                        "Edit", icon="edit",
                        on_click=lambda a=account: _open_edit_account_dialog(
                            a, on_saved=lambda: (player_filters.refresh(), player_table.refresh())
                        ),
                    ).props("flat dense no-caps color=primary")
                ui.button(
                    "Add Player", icon="person_add",
                    on_click=lambda a=account: _open_add_player_dialog(a),
                ).props("flat dense no-caps color=primary")
                toggle_button = ui.button(icon="expand_less" if expanded else "expand_more") \
                    .props("flat round dense")
                if not has_players:
                    toggle_button.props("disable")
                    toggle_button.tooltip("Add a player to this account to see them here.")

        if has_players:
            with ui.scroll_area().classes("h-72 w-full") as child_area:
                with ui.column().classes("w-full gap-2"):
                    for player, row in account_rows:
                        _render_player_card(player, row, show_roles=show_roles)
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
        else:
            ui.label("No players yet.").classes("text-sm text-grey-5 pl-9")


@ui.refreshable
def player_table() -> None:
    # Roles are about role *management*, a PowerAdmin-only capability (see
    # web_app_requirements.md > Account Management #3) - hidden for other roles.
    show_roles = role_switcher.is_at_least(Role.POWER_ADMIN)
    filtered_accounts = _filtered_accounts()

    if not filtered_accounts:
        if _visible_accounts():
            ui.label("No accounts match the current filters.").classes("text-sm text-grey-5")
        else:
            ui.label("⚠️ No data available").classes("text-sm text-grey-5")
        return

    # Paginate the account (parent) cards - simpler and more predictable than a
    # fixed-height outer scroll panel, and works for 1 account or 1000 alike.
    sorted_accounts = sorted(filtered_accounts, key=lambda a: a.account_name.lower())
    total_pages = max(1, -(-len(sorted_accounts) // ACCOUNTS_PAGE_SIZE))  # ceil division
    page = min(max(1, _get_accounts_page()), total_pages)
    start = (page - 1) * ACCOUNTS_PAGE_SIZE
    page_accounts = sorted_accounts[start:start + ACCOUNTS_PAGE_SIZE]

    for account in page_accounts:
        account_players = _account_players(account.id)
        account_rows = list(zip(account_players, _player_rows(account_players, show_roles=show_roles)))
        _render_account_card(account, account_rows, show_roles=show_roles)

    if total_pages > 1:
        def on_page_change(e) -> None:
            app.storage.user[ACCOUNTS_PAGE_KEY] = e.value
            player_table.refresh()

        with ui.row().classes("w-full justify-center"):
            ui.pagination(min=1, max=total_pages, value=page, direction_links=True, on_change=on_page_change)


def _render_player_details(player: Player) -> None:
    """The read-only "detail view" body: avatar + name header, then every
    Player column. Shared verbatim between the View dialog and part 1 of
    the Edit dialog, so the two always stay in sync.
    """
    account = next((a for a in accounts if a.id == player.account_id), None)
    alliance = next((a for a in alliances if a.id == player.alliance_id), None)
    kingdom_name = next((k.name for k in kingdoms if alliance and k.id == alliance.kingdom_id), "?")
    avatar_url = player.discord_guild_avatar_url or (account.discord_avatar_url if account else None)

    with ui.row().classes("items-center gap-3 w-full"):
        with ui.avatar(size="48px", color="grey-4", text_color="grey-8"):
            if avatar_url:
                ui.image(avatar_url).style("object-fit: cover")
            else:
                ui.icon("person")
        ui.label(player.kingshot_name).classes("text-base font-bold")

    with ui.column().classes("w-full gap-1"):
        _render_field("Player ID", str(player.id))
        _render_field("Account", account.account_name if account else f"Unknown (id={player.account_id})")
        _render_field("Kingdom", kingdom_name)
        _render_field("Alliance", alliance.name if alliance else "?")
        _render_field("Kingshot ID", player.kingshot_id)
        _render_field("Kingshot Name", player.kingshot_name)
        _render_field("Power", f"{player.power:,}")
        _render_field("Town Center Level", player.town_center_level)
        _render_field("Roles", ", ".join(r.value for r in player.roles) or "—")

        ui.separator().classes("my-3")
        ui.label("Discord").classes("text-xs font-bold text-grey-6 uppercase")
        _render_field("Discord Nickname", player.discord_nickname or "—")
        _render_copyable_field("Discord Guild Avatar URL", player.discord_guild_avatar_url)

        ui.separator().classes("my-3")
        ui.label("Audit").classes("text-xs font-bold text-grey-6 uppercase")
        owner_time_zone = account.time_zone if account else "UTC"
        _render_field("Created By", _resolve_account_name(player.create_account_id, account) if account else "—")
        _render_field("Created At", _format_dt(player.created_at, owner_time_zone))
        _render_field("Updated By", _resolve_account_name(player.update_account_id, account) if account else "—")
        _render_field("Updated At", _format_dt(player.updated_at, owner_time_zone))


def _open_view_player_dialog(player: Player) -> None:
    """Read-only detail view - every Player column, with the two audit-trail
    account IDs resolved to names per the requirements.
    """
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        ui.label("Player Details").classes("text-lg font-bold")
        _render_player_details(player)

        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=dialog.close).props("flat")

    dialog.open()


async def _do_discord_player_sync(player: Player, status_label: ui.label, on_updated) -> None:
    """Handler for the Edit dialog's "Sync from Discord" button. Re-verifies guild
    membership (bot-token based, same call used at Add Player time) and writes the
    fresh nickname/guild avatar back onto the player.

    NOTE: deliberately does NOT call player_table.refresh() - see
    app/pages/accounts.py's _do_discord_refresh() for why refreshing the outer
    card list while this dialog is open would close the dialog out from under
    the user. `on_updated` refreshes just the dialog's own detail-view section.
    """
    account = next((a for a in accounts if a.id == player.account_id), None)
    alliance = next((a for a in alliances if a.id == player.alliance_id), None)
    if account is None or account.account_type != AccountType.DISCORD_USER:
        ui.notify("This player's account has no Discord identity to sync from.", type="warning")
        return
    if alliance is None:
        ui.notify("Could not resolve this player's alliance.", type="negative")
        return

    status_label.classes(remove="text-negative text-positive")
    status_label.set_text("Checking guild membership…")
    check = await verify_guild_membership(alliance.discord_guild_id, account.discord_user_id)

    if check.result == MembershipResult.VERIFIED:
        player.discord_nickname = check.nickname
        player.discord_guild_avatar_url = build_guild_avatar_url(
            alliance.discord_guild_id, account.discord_user_id, check.avatar_hash
        )
        player.update_account_id = role_switcher.current_account_id()
        player.updated_at = datetime.utcnow()
        status_label.classes(add="text-positive")
        status_label.set_text(f"✓ Synced{f' — nick: {check.nickname}' if check.nickname else ''}")
        on_updated()
        ui.notify("Discord nickname/avatar synced.", type="positive")
    elif check.result == MembershipResult.NOT_A_MEMBER:
        status_label.classes(add="text-negative")
        status_label.set_text("✗ Not a member of this guild.")
    elif check.result == MembershipResult.BOT_FORBIDDEN:
        status_label.classes(add="text-negative")
        status_label.set_text("✗ Bot credentials are invalid (403).")
    elif check.result == MembershipResult.SERVER_ERROR:
        status_label.classes(add="text-negative")
        status_label.set_text("✗ Discord returned a server error — bot may have been removed.")
    else:
        status_label.classes(add="text-negative")
        status_label.set_text(f"✗ Unexpected error: {check.detail}")


def _open_edit_player_dialog(player: Player) -> None:
    account = next((a for a in accounts if a.id == player.account_id), None)
    is_discord_account = account is not None and account.account_type == AccountType.DISCORD_USER

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        # Part 1: identical read-only detail view to the View dialog, wrapped in its
        # own refreshable so a Discord sync can update it in place without touching
        # player_table (see _do_discord_player_sync's note on why).
        ui.label("Edit Player").classes("text-lg font-bold")

        @ui.refreshable
        def details_view() -> None:
            _render_player_details(player)

        details_view()

        # Part 2: the actual editable controls.
        ui.separator().classes("my-3")
        ui.label("Update").classes("text-xs font-bold text-grey-6 uppercase")

        kingshot_name_input = ui.input("Kingshot Name", value=player.kingshot_name) \
            .props("outlined").classes("w-full")
        power_input = ui.number("Power", value=player.power, min=0).props("outlined").classes("w-full")
        tc_select = ui.select(TOWN_CENTER_LEVELS, label="Town Center Level", value=player.town_center_level) \
            .props("outlined").classes("w-full")

        ui.label("Discord nickname and guild avatar are set from Discord, not edited directly.") \
            .classes("text-xs text-grey-6 mt-2")
        if is_discord_account:
            status_label = ui.label().classes("text-xs")
            ui.button(
                "Sync from Discord", icon="sync",
                on_click=lambda: _do_discord_player_sync(player, status_label, details_view.refresh),
            ).props("outlined dense no-caps")
        else:
            ui.label("Manual account - no Discord identity to sync.").classes("text-xs text-grey-6")

        def submit() -> None:
            if not kingshot_name_input.value:
                ui.notify("Kingshot name is required", type="warning")
                return
            player.kingshot_name = kingshot_name_input.value
            player.power = int(power_input.value or 0)
            player.town_center_level = tc_select.value or player.town_center_level
            player.update_account_id = role_switcher.current_account_id()
            player.updated_at = datetime.utcnow()
            dialog.close()
            player_filters.refresh()
            player_table.refresh()
            ui.notify("Player updated", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", on_click=submit).props("unelevated color=primary")

    # Catches every way the dialog can close (Save, Cancel, Esc, backdrop click) so a
    # Discord sync that was never explicitly "Saved" still shows up in the card list.
    dialog.on_value_change(lambda e: player_table.refresh() if not e.value else None)
    dialog.open()


def _open_add_player_dialog(account: Account) -> None:
    """Opens the player-details step directly for `account` - no account-picker
    step, since the account is already known (the card this button lives on).
    Admin/PowerAdmin are restricted to alliances they themselves belong to
    (see account_player._admin_alliance_ids()); SuperAdmin and a user adding a
    player to their own account are unrestricted, since either they can act on
    any alliance (SuperAdmin) or they may be joining a brand-new one (self-add).
    """
    allowed_alliance_ids = None
    if role_switcher.current_role() in (Role.ADMIN, Role.POWER_ADMIN):
        allowed_alliance_ids = _admin_alliance_ids()

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        _build_player_details_step(dialog, account, allowed_alliance_ids=allowed_alliance_ids)

    dialog.open()


def _build_player_details_step(
    dialog, account: Account, *, allowed_alliance_ids: set[int] | None = None,
) -> None:
    """Pick the alliance to join, verify guild membership - unless `account` is
    a manual (non-Discord) account, in which case verification is skipped
    entirely - then enter the Kingshot player details.

    `allowed_alliance_ids`, when given, restricts the Kingdom/Alliance choices
    to that set (see _open_add_player_dialog()) - an Admin/PowerAdmin adding a
    player to any account can still only place that player into an alliance
    they themselves belong to.
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

    kingdom_ids = {
        a.kingdom_id for a in alliances if allowed_alliance_ids is None or a.id in allowed_alliance_ids
    }
    kingdom_select = ui.select(
        {k.id: k.name for k in kingdoms if k.id in kingdom_ids}, label="Kingdom"
    ).props("outlined").classes("w-full")
    alliance_select = ui.select({}, label="Alliance").props("outlined").classes("w-full")
    guild_label = ui.label().classes("text-sm text-grey-6")
    verify_status = ui.label().classes("text-sm")

    def _sync_buttons() -> None:
        if not is_manual_account:
            _set_enabled(verify_button, bool(kingdom_select.value) and bool(alliance_select.value))
        _set_enabled(add_button, bool(verified_alliance_id["value"]))

    def on_kingdom_change() -> None:
        options = {
            a.id: a.name for a in alliances
            if a.kingdom_id == kingdom_select.value and (allowed_alliance_ids is None or a.id in allowed_alliance_ids)
        }
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
        # create_account_id follows the same "None = self-added" convention as
        # Account.create_account_id (see schema.py) - only set when an Admin/
        # PowerAdmin/SuperAdmin is adding this player to *someone else's*
        # account (per Greg's confirmation); update_account_id always records
        # whoever is acting, same as every other edit path in this app.
        acting_account_id = role_switcher.current_account_id()
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
            create_account_id=None if acting_account_id == account.id else acting_account_id,
            update_account_id=acting_account_id,
        ))
        dialog.close()
        # Refresh both: a new player can introduce a kingdom/alliance that wasn't
        # in the data-driven filter dropdowns before (see player_filters()), and
        # can also turn a zero-player account card into an expandable one.
        player_filters.refresh()
        player_table.refresh()
        ui.notify("Player added", type="positive")

    with ui.row().classes("w-full justify-end gap-2"):
        ui.button("Cancel", on_click=dialog.close).props("flat")
        add_button = ui.button("Add Player", on_click=submit).props("unelevated color=primary")

    _sync_buttons()  # buttons start disabled - nothing's selected/verified yet
