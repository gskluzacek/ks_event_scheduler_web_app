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
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto

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


def token_expiry_from(token_data: dict) -> datetime:
    """Discord's token response gives `expires_in` seconds, not an absolute time."""
    return datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 0))


async def refresh_access_token(refresh_token: str) -> dict:
    """Exchanges a stored refresh token for a new access token.

    Discord issues a NEW refresh_token on every use and invalidates the old
    one - callers must persist token_data['refresh_token'] from the response,
    not just re-use the one that was passed in.
    """
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        return response.json()


class RefreshOutcome(Enum):
    SUCCESS = auto()
    NO_CREDENTIALS = auto()   # account has no stored refresh_token - never logged in via OAuth here
    REAUTH_REQUIRED = auto()  # Discord rejected the refresh_token (revoked/expired) - user must log in again
    ERROR = auto()            # network error or other unexpected failure


@dataclass
class RefreshResult:
    outcome: RefreshOutcome
    username: str | None = None
    global_name: str | None = None
    avatar_url: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    detail: str | None = None


async def refresh_discord_identity(discord_user_id: str | None, refresh_token: str | None) -> RefreshResult:
    """Full refresh flow for the "Refresh from Discord" account action:
    exchange the stored refresh_token for a new access token, then re-fetch
    the user's identity fields with it. Callers are responsible for actually
    writing the returned fields back onto the Account.
    """
    if not discord_user_id or not refresh_token:
        return RefreshResult(RefreshOutcome.NO_CREDENTIALS)

    try:
        token_data = await refresh_access_token(refresh_token)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            # invalid_grant - Discord's standard response for a revoked/expired refresh token
            return RefreshResult(RefreshOutcome.REAUTH_REQUIRED, detail=str(exc))
        return RefreshResult(RefreshOutcome.ERROR, detail=str(exc))
    except httpx.HTTPError as exc:
        return RefreshResult(RefreshOutcome.ERROR, detail=str(exc))

    try:
        discord_user = await fetch_discord_user(token_data["access_token"])
    except httpx.HTTPError as exc:
        return RefreshResult(RefreshOutcome.ERROR, detail=str(exc))

    return RefreshResult(
        RefreshOutcome.SUCCESS,
        username=discord_user.get("username"),
        global_name=discord_user.get("global_name"),
        avatar_url=build_avatar_url(str(discord_user["id"]), discord_user.get("avatar")),
        access_token=token_data["access_token"],
        # Discord rotates the refresh token on every use - fall back to the old one
        # only if the response is missing it, which shouldn't normally happen.
        refresh_token=token_data.get("refresh_token", refresh_token),
        expires_at=token_expiry_from(token_data),
    )


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
