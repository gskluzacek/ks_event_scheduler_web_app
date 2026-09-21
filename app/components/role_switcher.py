"""
Fake role switcher for previewing role-gated UI without real role assignment.

Uses app.storage.user (see nicegui_llms.md Mental Model #8): a signed,
per-browser-session cookie store. That's the right scope here - it's *not*
shared across users, and it survives page reloads, so your "preview role"
sticks as you navigate.

Real role assignment (PowerAdmin granting roles to players) is out of scope
for this mock - this switcher exists purely so we can build and view every
page's role-gated behavior before that exists.

The account list backing current_account_id()/render() now comes from the
real accounts table (app/data/accounts.py) rather than sample_data.accounts.
But that's a DB read, and current_account_id() in particular is called
synchronously from deep inside helper functions scattered across nearly
every page module - including button on_click handlers (Discord refresh,
dialog Save/Add in app/pages/accounts.py and app/pages/players.py). Making
it genuinely async would mean threading `await` through all of those call
chains, in files this migration phase otherwise leaves untouched.

Instead, load_accounts() is awaited once per page load (from layout.frame(),
which every real page goes through) and the result is stashed in
app.storage.client - an in-memory dict NiceGUI keys by the current browser
connection (nicegui_llms.md Mental Model #8) and discards on disconnect/
reload. That's the right store here specifically *because* it's resolved
through NiceGUI's own client-tracking rather than a raw asyncio task/context:
a plain contextvars.ContextVar was tried first and confirmed (via a smoke
test simulating a button click) to NOT survive from the page-build task into
a later on_click handler's task - NiceGUI dispatches each event in its own
task, and contextvars don't propagate across independently-created tasks.
app.storage.client works from both. current_account_id()/render() then read
it synchronously for the rest of the connection's lifetime.
"""
from __future__ import annotations

from nicegui import app, ui

from app.data import accounts as accounts_repo
from app.models.schema import Account, Role
from app.components.safe_select import safe_select
from app.utils.storage import clear_page_state, get_valid_id

STORAGE_ACCOUNT_KEY = "preview_account_id"
STORAGE_ROLE_KEY = "preview_role"
NEW_USER_OPTION = "__new_user__"  # sentinel for "not registered yet" - never stored

_CLIENT_ACCOUNTS_KEY = "_role_switcher_accounts"


async def load_accounts() -> list[Account]:
    """Fetches the current account list from the DB and makes it available to
    current_account_id()/render() for the rest of this connection. Must be
    awaited once near the top of every page that uses this module - layout.frame()
    already does this, so any page built with `async with layout.frame(...):`
    gets it for free.
    """
    accounts = await accounts_repo.list_accounts()
    app.storage.client[_CLIENT_ACCOUNTS_KEY] = accounts
    return accounts


def _loaded_accounts() -> list[Account]:
    try:
        return app.storage.client[_CLIENT_ACCOUNTS_KEY]
    except KeyError:
        raise RuntimeError(
            "role_switcher.load_accounts() must be awaited (layout.frame() does this) "
            "before current_account_id()/render() are used."
        ) from None


def current_account_id() -> int:
    """The account ID saved for this browser session, falling back to the first account
    if it's missing or no longer valid (see app/utils/storage.py for why that can happen).
    """
    accounts = _loaded_accounts()
    return get_valid_id(STORAGE_ACCOUNT_KEY, {a.account_id for a in accounts}, accounts[0].account_id)


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
    """Renders the account + role picker. Call once, inside the shared header,
    after load_accounts() has populated this page load's account list (see
    layout.frame()).
    """
    accounts = _loaded_accounts()
    account_options = {a.account_id: a.account_name for a in accounts}
    account_options[NEW_USER_OPTION] = "— New User (not registered) —"
    role_options = {r.value: r.value for r in Role}

    with ui.row().classes("items-center gap-2"):
        # text-white/80 (not text-grey-6) so the label is actually legible on the dark header.
        ui.icon("visibility").classes("text-white/80")
        ui.label("Previewing as:").classes("text-sm text-white/80")

        # bg-white so the dropdown isn't the same color as the header behind it.
        account_select = safe_select(
            account_options,
            value=current_account_id(),
        ).props("dense outlined bg-color=white").classes("w-40 rounded")

        role_select = safe_select(
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
            # A different account/role sees different data, so the previous one's saved filters,
            # sorting, paging and expanded cards no longer apply - start the new view clean.
            clear_page_state()
            app.storage.user[STORAGE_ACCOUNT_KEY] = account_select.value
            app.storage.user[STORAGE_ROLE_KEY] = role_select.value
            ui.navigate.reload()  # simplest way to re-run page builders with the new role

        account_select.on_value_change(on_change)
        role_select.on_value_change(on_change)
