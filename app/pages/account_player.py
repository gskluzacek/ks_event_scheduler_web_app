"""
Shared helpers for the merged Account + Player management page.

Account and Player data overlap enough on-screen (an account's name, time
zone, and Discord identity vs. its players) that they're now managed from a
single page - see app/pages/players.py for the page itself. This module holds
the handful of things both app/pages/accounts.py (account-specific dialogs)
and app/pages/players.py (the page, player-specific dialogs, and the merged
account+player card list) need in common: audit-timestamp formatting, shared
dialog field renderers, account visibility/edit rules, and the "which
alliances does the current admin belong to" scoping helper.
"""
from __future__ import annotations

from datetime import datetime, timezone

from dateutil import tz as dateutil_tz
from nicegui import ui

from app.components import role_switcher
from app.models.sample_data import accounts, players
from app.models.schema import Account, Role


def _format_dt(dt: datetime | None, iana_name: str) -> str:
    """Renders a UTC-stored timestamp in the given IANA time zone (the
    account's own selected time zone) rather than raw UTC - audit timestamps
    are otherwise meaningless to a user who doesn't think in UTC.
    """
    if dt is None:
        return "—"
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    local_tz = dateutil_tz.gettz(iana_name)
    localized = aware.astimezone(local_tz) if local_tz else aware
    return localized.strftime("%Y-%m-%d %H:%M %Z")


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


def _set_enabled(element, enabled: bool) -> None:
    """Toggle a Quasar 'disable' prop - used for buttons that depend on prior
    steps being completed (e.g. Verify Guild Membership, then Add Player).
    """
    if enabled:
        element.props(remove="disable")
    else:
        element.props("disable")


def _resolve_account_name(account_id: int | None, owner: Account) -> str:
    """Resolves an audit column (create_account_id/update_account_id) to a
    display name. A None value means self-registered/self-added (see
    schema.py's Account/Player docstrings) - so it's the owning account's own
    name. Shared by both Account and Player detail views since the audit
    columns on both always resolve back to an account.
    """
    if account_id is None:
        return f"{owner.account_name} (self-registered)"
    match = next((a for a in accounts if a.id == account_id), None)
    return match.account_name if match else f"Unknown (id={account_id})"


def _visible_accounts() -> list[Account]:
    """Admin/PowerAdmin/SuperAdmin see every account, regardless of how many -
    or how few - players it has. A plain User or SchedulerAdmin only ever
    sees their own account.

    Per Greg's decision, account *visibility* is deliberately NOT
    alliance-scoped for Admin/PowerAdmin the way player visibility is (see
    _admin_alliance_ids() below and players.py's _visible_players()) - an
    Admin can see every account exists, just not every player inside it, and
    can't edit accounts other than their own (see _can_edit_account()).
    """
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return accounts
    return [a for a in accounts if a.id == role_switcher.current_account_id()]


def _can_edit_account(account_id: int) -> bool:
    """Everyone can edit their own account. Beyond that, only SuperAdmin can -
    Admin/PowerAdmin can view every account (see _visible_accounts()) and add
    players to them, but can no longer edit accounts other than their own.
    """
    return account_id == role_switcher.current_account_id() or role_switcher.current_role() == Role.SUPER_ADMIN


def _admin_alliance_ids() -> set[int]:
    """Alliance IDs the current viewer's own players belong to.

    Used to scope what an Admin/PowerAdmin can see and add across *every*
    account's player list: they can see every account (_visible_accounts()),
    but only the players in alliances they themselves belong to, and can only
    add new players into those same alliances. Not used for SuperAdmin (sees/
    adds everything, unrestricted) or for a plain User/SchedulerAdmin (only
    ever sees their own account's players anyway, via account_id, not
    alliance_id).
    """
    own_account_id = role_switcher.current_account_id()
    return {p.alliance_id for p in players if p.account_id == own_account_id}
