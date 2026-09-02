"""
Discord OAuth2 (identify scope only) - ported from discord_oauth_poc.py.

Per the corrected requirements flow, this module handles ONLY:
  - building the authorize URL with a CSRF `state` token
  - exchanging the returned `code` for an access token
  - fetching the Discord user's identity (id, username, avatar)

Guild membership verification (bot-token based) is intentionally NOT here -
it belongs to the "Add Player" flow (see auth/discord_guild.py), because per
web_app_requirements.md it only happens when a player is added to an
Alliance, not at registration/login time.

NOTE: this sandbox's network egress allowlist does not include discord.com,
so these calls cannot actually be exercised from here - the code mirrors the
tested PoC logic but you'll need to run it in your real environment to
verify end-to-end.
"""
from __future__ import annotations

import os
import secrets

import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/auth/discord/callback")

AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"


def generate_state() -> str:
    """CSRF state token - store this server-side (app.storage.user) and compare on callback."""
    return secrets.token_urlsafe(32)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    query = "&".join(f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())
    return f"{AUTHORIZE_URL}?{query}"


async def exchange_code_for_token(code: str) -> dict:
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        return response.json()


async def fetch_discord_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(USER_URL, headers=headers)
        response.raise_for_status()
        return response.json()


AVATAR_SIZE = 2048  # full-res; list/table thumbnails scale it down via CSS, not a smaller CDN fetch


def build_avatar_url(discord_user_id: str, avatar_hash: str | None) -> str | None:
    """Discord's /users/@me only returns an avatar *hash*, not a URL - this builds the
    actual (global) CDN URL. Returns None if the user has no custom avatar (caller should
    fall back to a generic icon rather than Discord's default-avatar CDN endpoint, since
    that requires the user's discriminator/index which we don't store).
    """
    if not avatar_hash:
        return None
    ext = "gif" if avatar_hash.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{discord_user_id}/{avatar_hash}.{ext}?size={AVATAR_SIZE}"
