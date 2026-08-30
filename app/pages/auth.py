"""
Account registration: real Discord OAuth2 (identify scope), no guild check.

Flow (per web_app_requirements.md > Account Registration flow):
  1. /register shows "Login with Discord" -> redirects to Discord's authorize URL
  2. Discord redirects back to the FastAPI route /auth/discord/callback with ?code&state
  3. We validate state, exchange the code, fetch the Discord identity,
     stash it in app.storage.user, and send the browser to /register/complete
  4. /register/complete asks for time zone (+ other account fields) and inserts
     into the in-memory `accounts` list on submit

NOTE: The callback is a plain FastAPI route (`@app.get`), not a `@ui.page` -
NiceGUI mounts on top of FastAPI, so ordinary FastAPI routes work side by
side with `@ui.page` routes for exactly this kind of external-redirect case
(nicegui_llms.md > Global App & Lifecycle > "Custom FastAPI routes").
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui

from app.auth import discord_oauth
from app.components.timezone_select import TimeZoneSelector
from app.models.sample_data import accounts
from app.models.schema import Account, AccountType, next_id

STATE_KEY = "oauth_state"
PENDING_DISCORD_USER_KEY = "pending_discord_user"


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
    async def discord_callback(request: Request, code: str = "", state: str = ""):
        expected_state = app.storage.user.get(STATE_KEY)
        if not state or state != expected_state:
            return RedirectResponse("/register?error=invalid_state")

        try:
            token_data = await discord_oauth.exchange_code_for_token(code)
            discord_user = await discord_oauth.fetch_discord_user(token_data["access_token"])
        except Exception as exc:  # noqa: BLE001 - surfacing any Discord/network failure to the user
            return RedirectResponse(f"/register?error={type(exc).__name__}")

        app.storage.user[PENDING_DISCORD_USER_KEY] = discord_user
        return RedirectResponse("/register/complete")


@ui.page("/register/complete")
def register_complete_page() -> None:
    ui.page_title("Complete Registration - Kingshot Scheduler")
    discord_user = app.storage.user.get(PENDING_DISCORD_USER_KEY)

    with ui.column().classes("w-full max-w-md mx-auto gap-4 p-12"):
        if not discord_user:
            ui.label("No pending Discord login found.").classes("text-negative")
            ui.button("Back to Register", on_click=lambda: ui.navigate.to("/register"))
            return

        ui.label(f"Welcome, {discord_user.get('username')}!").classes("text-2xl font-bold")
        ui.label("Just need a couple more details to finish setting up your account.")

        tz_selector = TimeZoneSelector()

        def submit() -> None:
            if not tz_selector.value:
                ui.notify("Please select a region and location", type="warning")
                return
            username = discord_user.get("username", "unknown")
            account = Account(
                id=next_id(),
                account_type=AccountType.DISCORD_USER,
                account_name=username,
                time_zone=tz_selector.value,
                discord_user_id=str(discord_user["id"]),
                discord_username=username,
                discord_global_name=discord_user.get("global_name"),
                discord_avatar_url=discord_user.get("avatar"),
            )
            accounts.append(account)
            del app.storage.user[PENDING_DISCORD_USER_KEY]
            ui.notify("Account created!", type="positive")
            ui.navigate.to("/dashboard")

        ui.button("Complete Registration", on_click=submit).props("unelevated color=primary")
