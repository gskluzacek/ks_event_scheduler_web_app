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

from models.sample_data import accounts, players
from models.schema import Role

STORAGE_ACCOUNT_KEY = "preview_account_id"
STORAGE_ROLE_KEY = "preview_role"


def current_account_id() -> int:
    return app.storage.user.get(STORAGE_ACCOUNT_KEY, accounts[0].id)


def current_role() -> Role:
    return Role(app.storage.user.get(STORAGE_ROLE_KEY, Role.USER.value))


def is_at_least(*allowed: Role) -> bool:
    """True if the current preview role is one of `allowed`, or SuperAdmin (which sees everything)."""
    role = current_role()
    return role == Role.SUPER_ADMIN or role in allowed


def render() -> None:
    """Renders the account + role picker. Call once, inside the shared header."""
    account_options = {a.id: a.discord_username for a in accounts}
    role_options = {r.value: r.value for r in Role}

    with ui.row().classes("items-center gap-2"):
        ui.icon("visibility").classes("text-grey-6")
        ui.label("Previewing as:").classes("text-sm text-grey-6")

        account_select = ui.select(
            account_options,
            value=current_account_id(),
        ).props("dense outlined").classes("w-40")

        role_select = ui.select(
            role_options,
            value=current_role().value,
        ).props("dense outlined").classes("w-44")

        def on_change() -> None:
            app.storage.user[STORAGE_ACCOUNT_KEY] = account_select.value
            app.storage.user[STORAGE_ROLE_KEY] = role_select.value
            ui.navigate.reload()  # simplest way to re-run page builders with the new role

        account_select.on_value_change(on_change)
        role_select.on_value_change(on_change)
