"""
Bot-token guild membership verification.

Per web_app_requirements.md > Player Joining Alliance flow, this runs when a
user adds a Player to an Alliance (not at login). Mirrors the PoC's
verification call and its three outcomes:

  200 -> member; returns the guild member object (nick, roles, user)
  404 -> not a member of that guild
  403 -> bot credentials are wrong
  5xx -> something else went wrong (bot kicked, Discord API error, etc.)

The PoC's known gap (404 vs other errors not distinguished) is fixed here:
each status is returned as an explicit, distinguishable result.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum, auto

import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")


class MembershipResult(Enum):
    VERIFIED = auto()
    NOT_A_MEMBER = auto()       # 404
    BOT_FORBIDDEN = auto()      # 403 - bad/revoked bot token, or bot lacks permission
    SERVER_ERROR = auto()       # 5xx - bot kicked, Discord outage, etc.
    UNKNOWN_ERROR = auto()      # anything else (network error, unexpected status)


@dataclass
class MembershipCheck:
    result: MembershipResult
    nickname: str | None = None
    roles: list[str] | None = None
    detail: str | None = None


async def verify_guild_membership(guild_id: str, discord_user_id: str) -> MembershipCheck:
    url = f"https://discord.com/api/guilds/{guild_id}/members/{discord_user_id}"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return MembershipCheck(MembershipResult.UNKNOWN_ERROR, detail=str(exc))

    if response.status_code == 200:
        member = response.json()
        return MembershipCheck(
            MembershipResult.VERIFIED,
            nickname=member.get("nick"),
            roles=member.get("roles", []),
        )
    if response.status_code == 404:
        return MembershipCheck(MembershipResult.NOT_A_MEMBER)
    if response.status_code == 403:
        return MembershipCheck(MembershipResult.BOT_FORBIDDEN, detail=response.text)
    if 500 <= response.status_code < 600:
        return MembershipCheck(MembershipResult.SERVER_ERROR, detail=response.text)
    return MembershipCheck(MembershipResult.UNKNOWN_ERROR, detail=f"{response.status_code}: {response.text}")
