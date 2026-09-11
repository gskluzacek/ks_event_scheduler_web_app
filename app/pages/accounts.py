from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import tz as dateutil_tz
from nicegui import app, ui

from app.auth.discord_oauth import RefreshOutcome, refresh_discord_identity
from app.components import layout, role_switcher
from app.components.timezone_select import TimeZoneSelector
from app.models.sample_data import accounts, alliances, kingdoms, players
from app.models.schema import Account, AccountType, Player, Role, next_id
from app.utils.filters import get_id_filter, get_text_filter, set_filter
from app.utils.rate_limit import check_and_record

REFRESH_RATE_LIMIT = 10
REFRESH_RATE_WINDOW = timedelta(hours=4)

FILTER_KINGDOM_KEY = "accounts_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "accounts_filter_alliance_id"
FILTER_NAME_KEY = "accounts_filter_name"

PAGE_KEY = "accounts_page"
PAGE_SIZE_KEY = "accounts_page_size"
PAGE_SIZE_OPTIONS = [3, 5, 10, 20, 50]
DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0]


def _visible_accounts() -> list[Account]:
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return accounts
    return [a for a in accounts if a.id == role_switcher.current_account_id()]


def _can_edit_account(account_id: int) -> bool:
    """Everyone can edit their own account (per requirements: "All users ...
    view and edit their personal information"); Admin/PowerAdmin can also
    edit other accounts. is_at_least() already folds SuperAdmin in.
    """
    return account_id == role_switcher.current_account_id() or role_switcher.is_at_least(
        Role.ADMIN, Role.POWER_ADMIN
    )


def _resolve_account_name(account_id: int | None, owner: Account) -> str:
    """Resolves an audit column (create_account_id/update_account_id) to a display
    name. A None create_account_id means the account self-registered via Discord
    OAuth (see schema.py's Account docstring) - so it's the owning account's own name.
    """
    if account_id is None:
        return f"{owner.account_name} (self-registered)"
    match = next((a for a in accounts if a.id == account_id), None)
    return match.account_name if match else f"Unknown (id={account_id})"


def _format_dt(dt: datetime | None, iana_name: str) -> str:
    """Renders a UTC-stored timestamp in the given IANA time zone (the account's
    own selected time zone) rather than raw UTC, per Greg's feedback - audit
    timestamps are otherwise meaningless to a user who doesn't think in UTC.
    """
    if dt is None:
        return "—"
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    local_tz = dateutil_tz.gettz(iana_name)
    localized = aware.astimezone(local_tz) if local_tz else aware
    return localized.strftime("%Y-%m-%d %H:%M %Z")


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


def _account_card_rows(rows: list[Account], *, show_admin_columns: bool) -> list[dict]:
    """One display-ready dict per account - same field set the old table columns
    used, just packaged for a card instead of a row.
    """
    player_count_by_account: dict[int, int] = {}
    for p in players:
        player_count_by_account[p.account_id] = player_count_by_account.get(p.account_id, 0) + 1

    result = []
    for a in rows:
        row = {
            "id": a.id,
            "avatar_url": a.discord_avatar_url,
            "account_name": a.account_name,
            "discord_global_name": a.discord_global_name,
            "player_count": player_count_by_account.get(a.id, 0),
            "time_zone": a.time_zone,
        }
        if show_admin_columns:
            row["account_type"] = a.account_type.value
            row["super_admin"] = a.is_super_admin
        result.append(row)
    return result


def _render_account_card(row: dict, *, show_admin_columns: bool) -> None:
    account = next(a for a in accounts if a.id == row["id"])
    with ui.card().classes("w-full").props("flat bordered"):
        with ui.row().classes("items-center gap-3 w-full no-wrap"):
            with ui.avatar(size="40px", color="grey-4", text_color="grey-8"):
                if row["avatar_url"]:
                    ui.image(row["avatar_url"]).style("object-fit: cover")
                else:
                    ui.icon("person")
            with ui.column().classes("gap-1 grow"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(row["account_name"]).classes("font-bold")
                    if row["discord_global_name"]:
                        ui.label(f"({row['discord_global_name']})").classes("text-sm text-grey-6")
                    if show_admin_columns:
                        ui.badge(row["account_type"]).props("color=grey-6")
                        if row["super_admin"]:
                            ui.badge("SuperAdmin").props("color=primary")
                with ui.row().classes("gap-x-6 gap-y-0 text-sm text-grey-7"):
                    ui.label(f"Players: {row['player_count']}")
                    ui.label(f"Time Zone: {row['time_zone']}")
            with ui.row().classes("gap-1"):
                ui.button("View", icon="visibility", on_click=lambda a=account: _open_view_account_dialog(a)) \
                    .props("flat dense no-caps")
                if _can_edit_account(account.id):
                    ui.button("Edit", icon="edit", on_click=lambda a=account: _open_edit_account_dialog(a)) \
                        .props("flat dense no-caps color=primary")


def _get_page_size() -> int:
    size = app.storage.user.get(PAGE_SIZE_KEY, DEFAULT_PAGE_SIZE)
    return size if size in PAGE_SIZE_OPTIONS else DEFAULT_PAGE_SIZE


def _get_page() -> int:
    return app.storage.user.get(PAGE_KEY, 1)


def _render_pagination_footer(*, page: int, page_size: int, total: int) -> None:
    """Records-per-page dropdown + 'X-Y of Z' range + first/prev/next/last -
    mirrors the standard Quasar table pagination footer (see Greg's screenshot),
    rebuilt in cards/buttons since these are ui.card rows, not a ui.table.
    """
    total_pages = max(1, -(-total // page_size))  # ceil division
    start = (page - 1) * page_size + 1
    end = min(page * page_size, total)

    def set_page(new_page: int) -> None:
        app.storage.user[PAGE_KEY] = new_page
        account_table.refresh()

    def on_page_size_change(e) -> None:
        app.storage.user[PAGE_SIZE_KEY] = e.value
        app.storage.user[PAGE_KEY] = 1  # page size changed - start back at page 1
        account_table.refresh()

    with ui.row().classes("w-full items-center justify-end gap-4 text-sm text-grey-7"):
        with ui.row().classes("items-center gap-2"):
            ui.label("Records per page:")
            ui.select(PAGE_SIZE_OPTIONS, value=page_size, on_change=on_page_size_change) \
                .props("dense borderless options-dense").classes("w-16")

        ui.label(f"{start}-{end} of {total}")

        with ui.row().classes("items-center gap-0"):
            ui.button(icon="first_page", on_click=lambda: set_page(1)) \
                .props("flat dense round").set_enabled(page > 1)
            ui.button(icon="chevron_left", on_click=lambda: set_page(page - 1)) \
                .props("flat dense round").set_enabled(page > 1)
            ui.button(icon="chevron_right", on_click=lambda: set_page(page + 1)) \
                .props("flat dense round").set_enabled(page < total_pages)
            ui.button(icon="last_page", on_click=lambda: set_page(total_pages)) \
                .props("flat dense round").set_enabled(page < total_pages)


@ui.refreshable
def account_table() -> None:
    show_admin_columns = role_switcher.is_any_admin()
    filtered = _filtered_accounts()

    if not filtered:
        if _visible_accounts():
            ui.label("No accounts match the current filters.").classes("text-sm text-grey-5")
        else:
            ui.label("⚠️ No data available").classes("text-sm text-grey-5")
        return

    # A plain User/SchedulerAdmin only ever has one visible account (see
    # _visible_accounts()) - no point showing pagination controls for one card.
    show_pagination = len(filtered) > 1
    page_size = _get_page_size() if show_pagination else len(filtered)
    total_pages = max(1, -(-len(filtered) // page_size))
    page = min(max(1, _get_page()), total_pages) if show_pagination else 1

    start_index = (page - 1) * page_size
    page_accounts = filtered[start_index:start_index + page_size]

    for row in _account_card_rows(page_accounts, show_admin_columns=show_admin_columns):
        _render_account_card(row, show_admin_columns=show_admin_columns)

    if show_pagination:
        _render_pagination_footer(page=page, page_size=page_size, total=len(filtered))


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


def _render_field(label: str, value: str) -> None:
    with ui.row().classes("w-full items-baseline gap-2"):
        ui.label(label).classes("text-sm text-grey-6 w-40 shrink-0")
        ui.label(value).classes("text-sm")


def _render_copyable_field(label: str, value: str | None) -> None:
    """Like _render_field, but truncates a long value (e.g. a Discord avatar
    URL), shows the full value in a hover tooltip, and adds a small button
    that copies the untruncated value to the clipboard.
    """
    with ui.row().classes("w-full items-center gap-2"):
        ui.label(label).classes("text-sm text-grey-6 w-40 shrink-0")
        if not value:
            ui.label("—").classes("text-sm")
            return
        truncated = value if len(value) <= 30 else value[:30] + "…"
        ui.label(truncated).classes("text-sm").tooltip(value)

        def copy_url(u: str = value) -> None:
            ui.clipboard.write(u)
            ui.notify("Copied to clipboard", type="positive")

        ui.button(icon="content_copy", on_click=copy_url).props("flat dense round size=sm")


def _render_account_details(account: Account) -> None:
    """The read-only "detail view" body: avatar + name header, then every
    Account column. Shared verbatim between the View dialog and part 1 of
    the Edit dialog, so the two always stay in sync.
    """
    with ui.row().classes("items-center gap-3 w-full"):
        with ui.avatar(size="48px", color="grey-4", text_color="grey-8"):
            if account.discord_avatar_url:
                ui.image(account.discord_avatar_url).style("object-fit: cover")
            else:
                ui.icon("person")
        ui.label(account.account_name).classes("text-base font-bold")

    with ui.column().classes("w-full gap-1"):
        _render_field("Account ID", str(account.id))
        _render_field("Account Type", account.account_type.value)
        _render_field("Account Name", account.account_name)
        _render_field("Time Zone", account.time_zone)
        _render_field("Super Admin", "Yes" if account.is_super_admin else "No")

        ui.separator().classes("my-3")
        ui.label("Discord").classes("text-xs font-bold text-grey-6 uppercase")
        _render_field("Discord User ID", account.discord_user_id or "—")
        _render_field("Discord Username", account.discord_username or "—")
        _render_field("Discord Global Name", account.discord_global_name or "—")
        _render_copyable_field("Discord Avatar URL", account.discord_avatar_url)

        ui.separator().classes("my-3")
        ui.label("Audit").classes("text-xs font-bold text-grey-6 uppercase")
        _render_field("Created By", _resolve_account_name(account.create_account_id, account))
        _render_field("Created At", _format_dt(account.created_at, account.time_zone))
        _render_field("Updated By", _resolve_account_name(account.update_account_id, account))
        _render_field("Updated At", _format_dt(account.updated_at, account.time_zone))


def _open_view_account_dialog(account: Account) -> None:
    """Read-only detail view - every Account column, with the two audit-trail
    account IDs resolved to names per the requirements.
    """
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        ui.label("Account Details").classes("text-lg font-bold")
        _render_account_details(account)

        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=dialog.close).props("flat")

    dialog.open()


async def _do_discord_refresh(account: Account, remaining_label: ui.label, on_updated) -> None:
    """Handler for the Edit dialog's "Refresh from Discord" button. Rate-limited
    per acting-user-per-target-account (see app/utils/rate_limit.py) regardless
    of whether the actor is the account owner or an Admin refreshing someone else.

    NOTE: this deliberately does NOT call account_table.refresh(). The dialog this
    button lives in was opened from inside account_table's refreshable container
    (via the account card's Edit button), and NiceGUI ties the dialog's lifetime to
    a "canary" element created in that same container (see nicegui/elements/dialog.py) -
    refreshing account_table while the dialog is still open destroys that canary and
    the dialog closes out from under the user. `on_updated` instead refreshes just
    the dialog's own detail-view section; the underlying card list picks up the
    change next time it's refreshed (e.g. when the dialog is closed).
    """
    allowed, remaining, retry_after = check_and_record(
        "discord_refresh", str(account.id), limit=REFRESH_RATE_LIMIT, window=REFRESH_RATE_WINDOW
    )
    if not allowed:
        minutes = max(1, int(retry_after.total_seconds() // 60))
        ui.notify(f"Refresh limit reached for this account - try again in ~{minutes} min.", type="warning")
        return

    result = await refresh_discord_identity(account.discord_user_id, account.discord_refresh_token)

    if result.outcome == RefreshOutcome.SUCCESS:
        account.discord_username = result.username
        account.discord_global_name = result.global_name
        account.discord_avatar_url = result.avatar_url
        account.discord_access_token = result.access_token
        account.discord_refresh_token = result.refresh_token
        account.discord_token_expires_at = result.expires_at
        account.update_account_id = role_switcher.current_account_id()
        account.updated_at = datetime.utcnow()
        remaining_label.set_text(f"{remaining} refresh(es) left in this 4-hour window.")
        on_updated()
        ui.notify("Discord details refreshed.", type="positive")
    elif result.outcome == RefreshOutcome.NO_CREDENTIALS:
        ui.notify(
            "No stored Discord credentials for this account - the user needs to log in "
            "again via Discord before this can be refreshed.", type="warning",
        )
    elif result.outcome == RefreshOutcome.REAUTH_REQUIRED:
        ui.notify(
            "Discord authorization has expired or was revoked - the user needs to log "
            "in again.", type="negative",
        )
    else:
        ui.notify(f"Could not refresh from Discord: {result.detail}", type="negative")


def _open_edit_account_dialog(account: Account) -> None:
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        # Part 1: identical read-only detail view to the View dialog, wrapped in its
        # own refreshable so a Discord refresh can update it in place without
        # touching account_table (see _do_discord_refresh's note on why).
        ui.label("Edit Account").classes("text-lg font-bold")

        @ui.refreshable
        def details_view() -> None:
            _render_account_details(account)

        details_view()

        # Part 2: the actual editable controls.
        ui.separator().classes("my-3")
        ui.label("Update").classes("text-xs font-bold text-grey-6 uppercase")

        # Account Name: editable only for manual accounts. Discord accounts derive
        # their identity from Discord, so they get a Refresh button instead
        # (see _do_discord_refresh for how the stored fields get updated).
        name_input = None
        if account.account_type == AccountType.MANUAL_USER:
            name_input = ui.input("Account Name", value=account.account_name) \
                .props("outlined").classes("w-full")
        else:
            remaining_label = ui.label("Discord username, name, and avatar cannot be edited directly.") \
                .classes("text-xs text-grey-6")
            ui.button(
                "Refresh from Discord", icon="refresh",
                on_click=lambda: _do_discord_refresh(account, remaining_label, details_view.refresh),
            ).props("outlined dense no-caps")

        ui.label("Time Zone").classes("text-sm text-grey-6 mt-2")
        tz_selector = TimeZoneSelector(value=account.time_zone)

        def submit() -> None:
            if name_input is not None and not name_input.value:
                ui.notify("Account name is required", type="warning")
                return
            if not tz_selector.value:
                ui.notify("Select a time zone", type="warning")
                return
            if name_input is not None:
                account.account_name = name_input.value
            account.time_zone = tz_selector.value
            account.update_account_id = role_switcher.current_account_id()
            account.updated_at = datetime.utcnow()
            dialog.close()
            account_filters.refresh()
            account_table.refresh()
            ui.notify("Account updated", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", on_click=submit).props("unelevated color=primary")

    # Catches every way the dialog can close (Save, Cancel, Esc, backdrop click) so a
    # Discord refresh that was never explicitly "Saved" still shows up in the card list.
    dialog.on_value_change(lambda e: account_table.refresh() if not e.value else None)
    dialog.open()
