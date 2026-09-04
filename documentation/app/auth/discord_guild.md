# app/auth/discord_guild.py

## Purpose
Provides server-side Discord guild membership verification using a bot token. It returns explicit status outcomes through typed enums and a result dataclass.

## Web Features and NiceGUI Usage Context
This module powers the `Add Player` interaction flow on the Players page.

NiceGUI page-level behavior enabled:
1. User selects kingdom/alliance in a dialog.
2. User clicks Verify Guild Membership.
3. Page calls `verify_guild_membership(...)`.
4. Page updates UI state based on `MembershipResult`.
5. On success, page unlocks player-detail inputs and optional guild avatar URL usage.

## User Interaction Processing Logic
Core processing path:
- Builds Discord API URL from guild/user IDs.
- Sends authenticated request using bot token.
- Maps HTTP outcomes:
  - 200: verified member (+ nickname/roles/avatar hash)
  - 404: not a member
  - 403: bot forbidden/bad credentials
  - 5xx: server/platform issues
  - exceptions/other: unknown error

`build_guild_avatar_url` constructs CDN URL for guild-specific avatars.

## Current Limitations
- Missing explicit guard when `DISCORD_BOT_TOKEN` is empty.
- No retry/backoff policy for transient failures.
- Result does not include rate-limit metadata.
- No circuit breaker for repeated upstream failure.

## Existing Issues
1. Config validation issue:
   - Empty bot token is not detected early; requests fail downstream.
2. Diagnostics issue:
   - Limited visibility into repeated upstream failures without logging.
3. Security hygiene issue:
   - No explicit warning path when 401/invalid token patterns occur (currently folded into unknown branch unless 403).

## Suggested Improvements
- Validate bot token presence at startup.
- Add structured logging with redaction.
- Distinguish 401 responses explicitly for clearer operator feedback.
