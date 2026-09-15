"""
Account-specific dialogs and mutations (view, add, edit, Discord refresh).

There's no longer a standalone /accounts page or route - account data is
surfaced directly from app/pages/players.py's account cards, since the two
overlapped enough on-screen that a separate page just duplicated the
account-level header shown atop every account's players. Shared visibility/
edit-permission rules and formatting helpers live in app/pages/account_player.py;
this module keeps only the account-mutation logic itself, called from
players.py's card buttons.

Every dialog-mutating function here takes an `on_saved`/`on_added` callback
rather than refreshing a container directly - players.py owns the refreshable
containers now, and calling back into it avoids a circular import between the
two page modules.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from nicegui import ui

from app.auth.discord_oauth import RefreshOutcome, refresh_discord_identity
from app.components import role_switcher
from app.components.timezone_select import TimeZoneSelector
from app.models.sample_data import accounts
from app.models.schema import Account, AccountType, next_id
from app.pages.account_player import _format_dt, _render_copyable_field, _render_field, _resolve_account_name
from app.utils.rate_limit import check_and_record

REFRESH_RATE_LIMIT = 10
REFRESH_RATE_WINDOW = timedelta(hours=4)


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

    NOTE: this deliberately does NOT refresh players.py's account card list.
    The dialog this button lives in was opened from inside that refreshable
    container (via the account card's Edit button), and NiceGUI ties the
    dialog's lifetime to a "canary" element created in that same container
    (see nicegui/elements/dialog.py) - refreshing it while the dialog is still
    open destroys that canary and the dialog closes out from under the user.
    `on_updated` instead refreshes just the dialog's own detail-view section;
    the underlying card list picks up the change next time it's refreshed
    (e.g. when the dialog is closed - see _open_edit_account_dialog's
    dialog.on_value_change).
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


def _open_edit_account_dialog(account: Account, *, on_saved) -> None:
    """`on_saved` is called after a successful Save, and also whenever the
    dialog closes any other way (Cancel/Esc/backdrop) - the latter catches a
    Discord refresh that was never explicitly "Saved" but still changed the
    account, so it shows up in the card list. Supplied by the caller
    (players.py) rather than refreshed directly here, to avoid a circular
    import between accounts.py and players.py.
    """
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
        # Part 1: identical read-only detail view to the View dialog, wrapped in its
        # own refreshable so a Discord refresh can update it in place without
        # closing the dialog (see _do_discord_refresh's note on why).
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
            on_saved()
            ui.notify("Account updated", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", on_click=submit).props("unelevated color=primary")

    # Catches every way the dialog can close (Save, Cancel, Esc, backdrop click) so a
    # Discord refresh that was never explicitly "Saved" still shows up in the card list.
    dialog.on_value_change(lambda e: on_saved() if not e.value else None)
    dialog.open()


def _open_add_account_dialog(*, on_added) -> None:
    """SuperAdmin-only (see players.py's players_page()) - creates a manual
    account with no players yet. `on_added` is supplied by the caller rather
    than refreshed directly here, to avoid a circular import with players.py.
    """
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Account").classes("text-lg font-bold")
        ui.label("Creates a manual account with no players yet - use each account "
                 "card's Add Player button afterwards to attach one.").classes("text-xs text-grey-6")

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
            on_added()
            ui.notify("Account added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add Account", on_click=submit).props("unelevated color=primary")

    dialog.open()
