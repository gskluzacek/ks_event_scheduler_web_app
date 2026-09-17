"""
First-run setup wizard.

app/setup_gate.py's middleware sends every request to the app's real pages
here until the SuperAdmin account exists, so this module has to work fully
standalone - no layout.frame(), no role_switcher, no reliance on any of the
still-fixture-backed data.

Three steps (per web_app_requirements.md, extended with a couple more
questions Greg answered directly rather than in that doc):
  1. Upload a CSV of IANA time zones (columns: region, location) -> time_zone table
  2. Create the initial SuperAdmin account via the normal Discord OAuth flow
     (see app/pages/auth.py) - lands on setup_admin_account_page() below
     instead of /register/complete, and sets is_super_admin=True
  3. Stub for a future kingdoms/alliances import - not built yet
"""
from __future__ import annotations

import csv
import io

from nicegui import app, ui

from app.auth import discord_oauth
from app.components.timezone_select import TimeZoneSelector
from app.data import accounts as accounts_repo
from app.data import time_zones as time_zones_repo
from app.models.schema import AccountType
from app.pages.auth import (
    PENDING_DISCORD_TOKEN_KEY,
    PENDING_DISCORD_USER_KEY,
    SETUP_MODE_KEY,
    STATE_KEY,
    discord_account_fields,
)


@ui.page("/setup")
async def setup_page() -> None:
    ui.page_title("Setup - Kingshot Scheduler")

    zones = await time_zones_repo.list_time_zones()
    account_exists = await accounts_repo.has_any_account()
    initial_step = "Kingdoms & Alliances" if account_exists else "Admin Account" if zones else "Time Zones"

    with ui.column().classes("w-full max-w-lg mx-auto gap-4 p-12"):
        ui.label("Kingshot Scheduler Setup").classes("text-2xl font-bold")

        with ui.stepper(value=initial_step).props("vertical").classes("w-full") as stepper:
            with ui.step("Time Zones"):
                ui.label("Upload a CSV of IANA time zones with columns: region, location.")
                status = ui.label(f"{len(zones)} time zones loaded." if zones else "")

                async def handle_upload(e) -> None:
                    text = await e.file.text()
                    reader = csv.DictReader(io.StringIO(text))
                    rows = [
                        {"region": row["region"].strip(), "location": row["location"].strip()}
                        for row in reader if row.get("region") and row.get("location")
                    ]
                    if not rows:
                        ui.notify("No valid rows found - check the region/location headers", type="warning")
                        return
                    await time_zones_repo.bulk_create_time_zones(rows)
                    status.set_text(f"{len(rows)} time zones loaded.")
                    ui.notify(f"Loaded {len(rows)} time zones", type="positive")
                    stepper.next()

                ui.upload(on_upload=handle_upload, auto_upload=True).props("accept=.csv").classes("w-full")
                with ui.stepper_navigation():
                    ui.button("Next", on_click=stepper.next)

            with ui.step("Admin Account"):
                ui.label("Create the initial SuperAdmin account via Discord.")

                def start_setup_login() -> None:
                    state = discord_oauth.generate_state()
                    app.storage.user[STATE_KEY] = state
                    app.storage.user[SETUP_MODE_KEY] = True
                    ui.navigate.to(discord_oauth.build_authorize_url(state))

                ui.button("Continue with Discord", icon="link", on_click=start_setup_login) \
                    .props("unelevated color=indigo-8")
                with ui.stepper_navigation():
                    ui.button("Back", on_click=stepper.previous).props("flat")

            with ui.step("Kingdoms & Alliances"):
                ui.label("Coming soon - for now, use Site Maintenance after setup.")
                with ui.stepper_navigation():
                    ui.button("Back", on_click=stepper.previous).props("flat")
                    ui.button("Go to Dashboard", on_click=lambda: ui.navigate.to("/dashboard")) \
                        .props("unelevated color=primary")


@ui.page("/setup/admin-account")
async def setup_admin_account_page() -> None:
    """Discord OAuth lands here (instead of /register/complete) when the login
    was started from the setup wizard - see auth.discord_callback()."""
    ui.page_title("Setup - Admin Account")
    discord_user = app.storage.user.get(PENDING_DISCORD_USER_KEY)

    with ui.column().classes("w-full max-w-md mx-auto gap-4 p-12"):
        if not discord_user:
            ui.label("No pending Discord login found.").classes("text-negative")
            ui.button("Back to Setup", on_click=lambda: ui.navigate.to("/setup"))
            return

        ui.label(f"Welcome, {discord_user.get('username')}!").classes("text-2xl font-bold")
        ui.label("This account will be the site's SuperAdmin.")

        zones = await time_zones_repo.list_time_zones()
        tz_selector = TimeZoneSelector(zones)

        async def submit() -> None:
            if not tz_selector.value:
                ui.notify("Please select a region and location", type="warning")
                return
            token_data = app.storage.user.get(PENDING_DISCORD_TOKEN_KEY, {})
            await accounts_repo.create_account(
                account_type=AccountType.DISCORD_USER,
                time_zone=tz_selector.value,
                is_super_admin=True,
                **discord_account_fields(discord_user, token_data),
            )
            app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
            app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)
            ui.notify("SuperAdmin account created!", type="positive")
            ui.navigate.to("/setup")

        ui.button("Create SuperAdmin Account", on_click=submit).props("unelevated color=primary")
