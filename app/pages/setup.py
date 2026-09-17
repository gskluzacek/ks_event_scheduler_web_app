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
     (see app/pages/auth.py), landing back on THIS page (not a separate one -
     see the "Admin Account" step below) with is_super_admin=True
  3. Stub for a future kingdoms/alliances import - not built yet
"""
from __future__ import annotations

import csv
import io

from nicegui import app, ui
from sqlalchemy.exc import IntegrityError

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
async def setup_page(error: str = "", authorized: str = "") -> None:
    ui.page_title("Setup - Kingshot Scheduler")

    zones = await time_zones_repo.list_time_zones()
    account_exists = await accounts_repo.has_any_account()
    initial_step = "Kingdoms & Alliances" if account_exists else "Admin Account" if zones else "Time Zones"

    # A pending Discord identity is only trustworthy immediately after the OAuth
    # round trip that set it - discord_callback() marks that redirect with
    # ?authorized=1. Any other request to this page (a plain reload, reopening
    # the tab later, restarting the app - all common when wiping the DB during
    # testing) must NOT resurrect a stale identity left over from some earlier,
    # unrelated login: app.storage.user is a persistent per-browser cookie, so
    # it survives a deleted database file just fine. Going Back/Next between
    # steps is a client-side-only stepper change, not a new request, so this
    # never fires mid-wizard - only on an actual fresh page load.
    if authorized:
        discord_user = app.storage.user.get(PENDING_DISCORD_USER_KEY)
    else:
        discord_user = None
        app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
        app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)

    with ui.column().classes("w-full max-w-lg mx-auto gap-4 p-12"):
        ui.label("Kingshot Scheduler Setup").classes("text-2xl font-bold")
        if error:
            ui.label(f"Discord login didn't complete ({error}) - please try again.") \
                .classes("text-negative")

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
                    inserted = await time_zones_repo.bulk_create_time_zones(rows)
                    # Mutate in place (not `zones = ...`) so the same list object is also
                    # what any already-built TimeZoneSelector below is holding onto.
                    zones[:] = await time_zones_repo.list_time_zones()
                    skipped = len(rows) - inserted
                    status.set_text(f"{len(zones)} time zones loaded.")
                    message = f"Loaded {inserted} new time zones"
                    message += f" ({skipped} already loaded, skipped)" if skipped else ""
                    ui.notify(message, type="positive" if inserted else "info")
                    stepper.next()

                ui.upload(on_upload=handle_upload, auto_upload=True).props("accept=.csv").classes("w-full")
                with ui.stepper_navigation():

                    def go_to_admin_account() -> None:
                        # Without this, clicking Next with nothing ever uploaded lands on a
                        # time zone picker with zero regions/locations to choose from.
                        if not zones:
                            ui.notify("Please upload a time zone CSV file first", type="warning")
                            return
                        stepper.next()

                    ui.button("Next", on_click=go_to_admin_account)

            with ui.step("Admin Account"):
                if account_exists:
                    # Reached via Back from step 3 after setup already completed (in this
                    # same page load or an earlier one) - discord_user is always None here
                    # (nothing pending survives once an account exists), so there's nothing
                    # left to do. Showing "Continue with Discord" in this state would look
                    # live but do nothing useful if clicked - see start_setup_login()'s
                    # guard below for what actually happens if it somehow still is clicked.
                    ui.label("The SuperAdmin account has already been created.").classes("font-bold")
                elif discord_user:
                    # Back from Discord (success) - collect the account's time zone right
                    # here, still inside the wizard, rather than sending the user to yet
                    # another page. "Back" from step 3 lands right back on this same form,
                    # with no need to re-authorize, since discord_user is still pending.
                    ui.label(f"Welcome, {discord_user.get('username')}!").classes("font-bold")
                    ui.label("This account will be the site's SuperAdmin.")
                    tz_selector = TimeZoneSelector(zones)

                    async def submit() -> None:
                        if not tz_selector.value:
                            ui.notify("Please select a region and location", type="warning")
                            return
                        # Guards against the exact bug this closure exists to prevent: this
                        # page's steps are rendered once and just shown/hidden client-side
                        # after that, so a stale render of this step (e.g. reached via the
                        # stepper's Back button after setup already completed once, in
                        # another step or another tab) must not be allowed to insert a
                        # second account - see start_setup_login()'s matching guard below.
                        if await accounts_repo.has_any_account():
                            ui.notify("An admin account already exists - setup is already complete.", type="warning")
                            app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
                            app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)
                            ui.navigate.to("/setup")
                            return
                        token_data = app.storage.user.get(PENDING_DISCORD_TOKEN_KEY, {})
                        try:
                            await accounts_repo.create_account(
                                account_type=AccountType.DISCORD_USER,
                                time_zone=tz_selector.value,
                                is_super_admin=True,
                                **discord_account_fields(discord_user, token_data),
                            )
                        except IntegrityError:
                            # Last-resort net under the has_any_account() check above, for
                            # the truly-concurrent case (e.g. two tabs submitting at once).
                            ui.notify("An account for this Discord user already exists.", type="warning")
                            app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
                            app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)
                            ui.navigate.to("/setup")
                            return
                        app.storage.user.pop(PENDING_DISCORD_USER_KEY, None)
                        app.storage.user.pop(PENDING_DISCORD_TOKEN_KEY, None)
                        ui.notify("SuperAdmin account created!", type="positive")
                        ui.navigate.to("/setup")

                    ui.button("Create SuperAdmin Account", on_click=submit).props("unelevated color=primary")
                else:
                    ui.label("Create the initial SuperAdmin account via Discord.")

                    async def start_setup_login() -> None:
                        # Same stale-render concern as submit() above, checked here too so a
                        # reused "Continue with Discord" button doesn't even burn the round
                        # trip to Discord before finding out setup's already done.
                        if await accounts_repo.has_any_account():
                            ui.notify("Setup is already complete.", type="info")
                            ui.navigate.to("/setup")
                            return
                        # Also shouldn't be reachable given step 1's own guard, but this step's
                        # body renders regardless of which step is active, so a stale render
                        # (or a stepper header click, if that's ever enabled) could otherwise
                        # get here with nothing to build the time zone picker from.
                        if not zones:
                            ui.notify("Please upload a time zone CSV file first", type="warning")
                            stepper.previous()
                            return
                        state = discord_oauth.generate_state()
                        app.storage.user[STATE_KEY] = state
                        app.storage.user[SETUP_MODE_KEY] = True
                        ui.navigate.to(discord_oauth.build_authorize_url(state))

                    ui.button("Continue with Discord", icon="link", on_click=start_setup_login) \
                        .props("unelevated color=indigo-8")

                with ui.stepper_navigation():
                    ui.button("Back", on_click=stepper.previous).props("flat")
                    if account_exists:
                        ui.button("Next", on_click=stepper.next).props("unelevated color=primary")

            with ui.step("Kingdoms & Alliances"):
                ui.label("Coming soon - for now, use Site Maintenance after setup.")
                with ui.stepper_navigation():
                    ui.button("Back", on_click=stepper.previous).props("flat")
                    ui.button("Go to Dashboard", on_click=lambda: ui.navigate.to("/dashboard")) \
                        .props("unelevated color=primary")
