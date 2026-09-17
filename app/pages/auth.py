"""
Account registration: real Discord OAuth2 (identify scope), no guild check.

Flow (per web_app_requirements.md > Account Registration flow):
  1. /register shows "Login with Discord" -> redirects to Discord's authorize URL
  2. Discord redirects back to the FastAPI route /auth/discord/callback with
     ?code&state on success, or ?error=... (e.g. "access_denied" if the user
     clicks Cancel on Discord's consent screen) instead of ?code
  3. On success, we validate state, exchange the code, fetch the Discord
     identity, stash it in app.storage.user, and send the browser to
     /register/complete. On any failure, we send it back to wherever the
     login was started from (/register, or /setup if SETUP_MODE_KEY was set),
     with ?error=... so that page can show what went wrong.
  4. /register/complete asks for time zone (+ other account fields) and inserts
     into the in-memory `accounts` list on submit

NOTE: The callback is a plain FastAPI route (`@app.get`), not a `@ui.page` -
NiceGUI mounts on top of FastAPI, so ordinary FastAPI routes work side by
side with `@ui.page` routes for exactly this kind of external-redirect case
(nicegui_llms.md > Global App & Lifecycle > "Custom FastAPI routes").

The same Discord login is reused by the first-run setup wizard
(app/pages/setup.py) to create the initial, real (DB-backed) SuperAdmin
account. SETUP_MODE_KEY, set right before redirecting to Discord, is how
discord_callback() tells the two flows apart and sends the browser back to
the right place either way; discord_account_fields() is the bit of Discord ->
Account field mapping both completion flows need.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui

from app.auth import discord_oauth
from app.components.timezone_select import TimeZoneSelector
from app.data import accounts as accounts_repo
from app.models.sample_data import accounts, time_zones
from app.models.schema import Account, AccountType, next_id

STATE_KEY = "oauth_state"
SETUP_MODE_KEY = "setup_mode"
PENDING_DISCORD_USER_KEY = "pending_discord_user"
PENDING_DISCORD_TOKEN_KEY = "pending_discord_token"


def discord_account_fields(discord_user: dict, token_data: dict) -> dict:
    """Discord identity -> Account field mapping shared by /register/complete
    and the setup wizard's admin-account step, so the two stay in sync."""
    username = discord_user.get("username", "unknown")
    return dict(
        account_name=username,
        discord_user_id=str(discord_user["id"]),
        discord_username=username,
        discord_global_name=discord_user.get("global_name"),
        discord_avatar_url=discord_oauth.build_avatar_url(
            str(discord_user["id"]), discord_user.get("avatar")
        ),
        discord_access_token=token_data.get("access_token"),
        discord_refresh_token=token_data.get("refresh_token"),
        discord_token_expires_at=(
            discord_oauth.token_expiry_from(token_data) if token_data else None
        ),
    )


@ui.page("/register")
def register_page() -> None:
    ui.page_title("Register - Kingshot Scheduler")

    with ui.column().classes("w-full items-center justify-center gap-6 p-12"):
        ui.label("Kingshot Scheduler").classes("text-3xl font-bold")
        ui.label("Register your account with Discord to get started.").classes("text-grey-7")

        def start_login() -> None:
            state = discord_oauth.generate_state()
            app.storage.user[STATE_KEY] = state
            ui.navigate.to(discord_oauth.build_authorize_url(state))

        ui.button("Login with Discord", icon="link", on_click=start_login) \
            .props("unelevated color=indigo-8 size=lg")

        ui.label(
            "This sandbox can't actually reach discord.com, so this button "
            "will error here - the flow is wired for your real environment."
        ).classes("text-xs text-grey-5 italic")


def register_fastapi_routes() -> None:
    """Registers the OAuth callback as a plain FastAPI route. Call once from main.py."""

    @app.get("/auth/discord/callback")
    async def discord_callback(request: Request, code: str = "", state: str = "", error: str = ""):
        setup_mode = app.storage.user.pop(SETUP_MODE_KEY, False)
        error_redirect = "/setup" if setup_mode else "/register"
        expected_state = app.storage.user.get(STATE_KEY)

        if error:  # e.g. "access_denied" - the user clicked Cancel on Discord's consent screen
            return RedirectResponse(f"{error_redirect}?error={error}")
        if not state or state != expected_state:
            return RedirectResponse(f"{error_redirect}?error=invalid_state")

        try:
            token_data = await discord_oauth.exchange_code_for_token(code)
            discord_user = await discord_oauth.fetch_discord_user(token_data["access_token"])
        except Exception as exc:  # noqa: BLE001 - surfacing any Discord/network failure to the user
            return RedirectResponse(f"{error_redirect}?error={type(exc).__name__}")

        # Stash the tokens alongside the identity - the completion page needs them
        # to populate Account.discord_access_token/discord_refresh_token so the
        # "Refresh from Discord" action (app/pages/accounts.py) works later without
        # asking the user to log in again.
        if setup_mode and await accounts_repo.has_any_account():
            # Setup already completed (e.g. via another tab, or this same redirect URL
            # replayed from browser history) while this login was in flight - don't
            # stash a second pending identity for the wizard to act on.
            return RedirectResponse("/setup")
        app.storage.user[PENDING_DISCORD_USER_KEY] = discord_user
        app.storage.user[PENDING_DISCORD_TOKEN_KEY] = token_data
        return RedirectResponse("/setup?authorized=1" if setup_mode else "/register/complete?authorized=1")


@ui.page("/register/complete")
def register_complete_page(authorized: str = "") -> None:
    ui.page_title("Complete Registration - Kingshot Scheduler")

    # Same staleness concern as setup.setup_page(): app.storage.user is a
    # persistent per-browser cookie, so without this check a plain reload or
    # much later reopening of this URL could resurrect a long-dead pending
    # Discord login instead of correctly saying "no pending login found".
    if authorized:
        discord_user = app.storage.user.get(PENDING_DISCORD_USER_KEY)
    else:
        discord_user = None
        app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
        app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)

    with ui.column().classes("w-full max-w-md mx-auto gap-4 p-12"):
        if not discord_user:
            ui.label("No pending Discord login found.").classes("text-negative")
            ui.button("Back to Register", on_click=lambda: ui.navigate.to("/register"))
            return

        ui.label(f"Welcome, {discord_user.get('username')}!").classes("text-2xl font-bold")
        ui.label("Just need a couple more details to finish setting up your account.")

        tz_selector = TimeZoneSelector(time_zones)

        def submit() -> None:
            if not tz_selector.value:
                ui.notify("Please select a region and location", type="warning")
                return
            token_data = app.storage.user.get(PENDING_DISCORD_TOKEN_KEY, {})
            account = Account(
                account_id=next_id(),
                account_type=AccountType.DISCORD_USER,
                time_zone=tz_selector.value,
                **discord_account_fields(discord_user, token_data),
            )
            accounts.append(account)
            del app.storage.user[PENDING_DISCORD_USER_KEY]
            app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)
            ui.notify("Account created!", type="positive")
            ui.navigate.to("/dashboard")

        ui.button("Complete Registration", on_click=submit).props("unelevated color=primary")
