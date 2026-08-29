"""
Discord OAuth2 + Guild-Membership Proof of Concept
===================================================

Flow:
  1. User clicks "Login with Discord" -> Discord's consent screen (scope=identify only).
  2. Discord redirects back to /callback?code=...&state=...
  3. We exchange the code for a short-lived access token (proves "this really is the user").
  4. We call /users/@me with that token -> Discord ID + username.
  5. We use our BOT token (separate, more privileged) to call
     GET /guilds/{guild_id}/members/{user_id}.
     200 = member, 404 = not a member. This is the authoritative check.

Why bot-token verification instead of the OAuth `guilds` scope?
  + Live, authoritative — can't be spoofed by a stale/cached guild list
  + Works even if the guild isn't "visible" in the user's OAuth guild list
  + Leaves room to gate by role/nickname later (same endpoint returns roles)
  - Your bot must already be a member of the target guild

Setup:
  1. cp .env.example .env   and fill in the four values (see comments in that file).
  2. pip install nicegui httpx python-dotenv
  3. python discord_oauth_poc.py
  4. Visit http://localhost:8080
"""

import os
import secrets
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui

load_dotenv()

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ["DISCORD_GUILD_ID"]
REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")

DISCORD_API = "https://discord.com/api/v10"
AUTHORIZE_URL = "https://discord.com/oauth2/authorize"

# CSRF protection: state tokens we've issued but not yet redeemed.
# PoC-only: a process-local set. In production use app.storage.user
# (or a DB/Redis) so it survives multi-worker deployments.
_pending_states: set[str] = set()


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
@ui.page("/")
def index() -> None:
    ui.label("Discord Guild-Gated Login — PoC").classes("text-2xl font-bold mb-4")

    if app.storage.user.get("discord_user"):
        _show_logged_in()
    else:
        _show_login_button()


def _show_login_button() -> None:
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    authorize_url = f"{AUTHORIZE_URL}?{urlencode(params)}"

    print(authorize_url)

    ui.button("Login with Discord", icon="login") \
        .props(f'href="{authorize_url}" tag=a unelevated color=primary')


def _show_logged_in() -> None:
    user = app.storage.user["discord_user"]
    member = app.storage.user["discord_member"]
    is_member = app.storage.user["is_guild_member"]

    with ui.card():
        ui.label(f"Logged in as {user['username']}").classes("text-lg")
        ui.label(f"Global name: {user.get('global_name', '(none)')}").classes("text-sm text-grey")
        ui.label(f"Guild Nickname: {member.get('nick', '(none)')}").classes("text-sm text-grey")
        ui.label(f"Discord ID: {user['id']}").classes("text-sm text-grey")
        if is_member:
            ui.label("✅ Verified member of the required guild").classes("text-positive font-bold")
        else:
            ui.label("❌ Not a member of the required guild").classes("text-negative font-bold")

    ui.button("Log out", on_click=_logout).props("flat")


def _logout() -> None:
    app.storage.user.clear()
    ui.navigate.to("/")


# --------------------------------------------------------------------------
# OAuth callback — a plain FastAPI route mounted alongside NiceGUI's pages
# --------------------------------------------------------------------------
@app.get("/callback")
async def discord_callback(request: Request):
    print("callback url:", request.url)
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or state not in _pending_states:
        return RedirectResponse("/")
    _pending_states.discard(state)

    async with httpx.AsyncClient() as client:
        # Step 1: exchange the authorization code for an access token
        token_resp = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # print(token_resp.json())
        # {
        #   'token_type': 'Bearer',
        #   'access_token': 'MTUx...IA722M32',
        #   'expires_in': 604800,
        #   'refresh_token': 'b4rU...bqIt',
        #   'scope': 'identify'
        # }
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Step 2: fetch the user's identity
        user_resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # print(user_resp.json())
        # {
        #   'id': '1539...48404',
        #   'username': 'marla_..._2026',
        #   'avatar': '8618f...5fb8a7',
        #   'discriminator': '0',
        #   'public_flags': 0,
        #   'flags': 0,
        #   'banner': None,
        #   'accent_color': 13873571,
        #   'global_name': 'Marla...r',
        #   'avatar_decoration_data': None,
        #   'collectibles': None,
        #   'display_name_styles': None,
        #   'banner_color': '#d3b1a3',
        #   'clan': None,
        #   'primary_guild': None,
        #   'mfa_enabled': False,
        #   'locale': 'en-US',
        #   'premium_type': 0
        # }
        user_resp.raise_for_status()
        discord_user = user_resp.json()

        # Step 3: verify guild membership server-side with the BOT token
        member_resp = await client.get(
            f"{DISCORD_API}/guilds/{GUILD_ID}/members/{discord_user['id']}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"},
        )
        # print(member_resp.json())
        # {
        #   'avatar': None,
        #   'banner': None,
        #   'communication_disabled_until': None,
        #   'flags': 0,
        #   'joined_at': '2026-08-20T04:34:25.145000+00:00',
        #   'nick': 'Bri...den',
        #   'pending': False,
        #   'premium_since': None,
        #   'roles': [],
        #   'unusual_dm_activity_until': None,
        #   'collectibles': None,
        #   'display_name_styles': None,
        #   'user': {
        #       'id': '153...48404',
        #       'username': 'marla_..._2026',
        #       'avatar': '8618f...5fb8a7',
        #       'discriminator': '0',
        #       'public_flags': 0,
        #       'flags': 0,
        #       'banner': None,
        #       'accent_color': 13873571,
        #       'global_name': 'Marla...',
        #       'avatar_decoration_data': None,
        #       'collectibles': None,
        #       'display_name_styles': None,
        #       'banner_color': '#d3b1a3',
        #       'clan': None,
        #       'primary_guild': None
        #   },
        #   'mute': False,
        #   'deaf': False
        # }
        discord_member = member_resp.json()
        is_member = member_resp.status_code == 200

    # app.storage.user is a signed cookie-backed session — per user, survives reloads
    app.storage.user["discord_user"] = discord_user
    app.storage.user["discord_member"] = discord_member
    app.storage.user["is_guild_member"] = is_member
    return RedirectResponse("/")


# --------------------------------------------------------------------------
ui.run(
    title="Discord OAuth PoC",
    storage_secret=os.environ.get("NICEGUI_STORAGE_SECRET", "change-me-in-production"),
    port=8080,
)
