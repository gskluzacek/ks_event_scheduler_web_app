"""
Fake role switcher for previewing role-gated UI without real role assignment.

Uses app.storage.user (see nicegui_llms.md Mental Model #8): a signed,
per-browser-session cookie store. That's the right scope here - it's *not*
shared across users (unlike the module-level sample_data lists), and it
survives page reloads, so your "preview role" sticks as you navigate.

Real role assignment (PowerAdmin granting roles to players) is out of scope
for this mock - this switcher exists purely so we can build and view every
page's role-gated behavior before that exists.
"""
from __future__ import annotations

from nicegui import app, ui

from app.models.sample_data import accounts, players
from app.models.schema import Role
from app.utils.storage import get_valid_id

STORAGE_ACCOUNT_KEY = "preview_account_id"
STORAGE_ROLE_KEY = "preview_role"
NEW_USER_OPTION = "__new_user__"  # sentinel for "not registered yet" - never stored


def current_account_id() -> int:
    """The account ID saved for this browser session, falling back to the first account
    if it's missing or no longer valid (see app/utils/storage.py for why that can happen).
    """
    return get_valid_id(STORAGE_ACCOUNT_KEY, {a.id for a in accounts}, accounts[0].id)


def current_role() -> Role:
    return Role(app.storage.user.get(STORAGE_ROLE_KEY, Role.USER.value))


def is_at_least(*allowed: Role) -> bool:
    """True if the current preview role is one of `allowed`, or SuperAdmin (which sees everything)."""
    role = current_role()
    return role == Role.SUPER_ADMIN or role in allowed


def is_any_admin() -> bool:
    """True for Admin, PowerAdmin, or SchedulerAdmin (or SuperAdmin, via is_at_least's rule) -
    i.e. any elevated role, as opposed to a plain User. Shared by pages that gate a
    column or filter behind "any admin-type role" rather than a specific one.
    """
    return is_at_least(Role.ADMIN, Role.POWER_ADMIN, Role.SCHEDULER_ADMIN)


def render() -> None:
    """Renders the account + role picker. Call once, inside the shared header."""
    account_options = {a.id: a.account_name for a in accounts}
    account_options[NEW_USER_OPTION] = "— New User (not registered) —"
    role_options = {r.value: r.value for r in Role}

    with ui.row().classes("items-center gap-2"):
        # text-white/80 (not text-grey-6) so the label is actually legible on the dark header.
        ui.icon("visibility").classes("text-white/80")
        ui.label("Previewing as:").classes("text-sm text-white/80")

        # bg-white so the dropdown isn't the same color as the header behind it.
        account_select = ui.select(
            account_options,
            value=current_account_id(),
        ).props("dense outlined bg-color=white").classes("w-40 rounded")

        role_select = ui.select(
            role_options,
            value=current_role().value,
        ).props("dense outlined bg-color=white").classes("w-44 rounded")

        def on_change() -> None:
            if account_select.value == NEW_USER_OPTION:
                # Don't persist this - it's not a real account. Just send the browser to the
                # registration flow so you can exercise it; picking a real account afterwards
                # resets things back to normal.
                ui.navigate.to("/register")
                return
            app.storage.user[STORAGE_ACCOUNT_KEY] = account_select.value
            app.storage.user[STORAGE_ROLE_KEY] = role_select.value
            ui.navigate.reload()  # simplest way to re-run page builders with the new role

        account_select.on_value_change(on_change)
        role_select.on_value_change(on_change)
