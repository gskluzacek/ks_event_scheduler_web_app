"""
Simple sliding-window rate limiter backed by app.storage.user.

Used for actions that need a "N per window" cap tracked per *acting* browser
session - e.g. how many times someone can trigger the Discord refresh in a
given period. Scoping by `key` (rather than one counter per bucket) matters
because the acting user isn't always the target of the action: an Admin
refreshing another account's Discord details should get their own allowance
per target account, tracked under the Admin's own storage.

Stored as plain ISO timestamp strings (not datetimes) since app.storage.user
persists to disk as JSON - see nicegui_llms.md Mental Model #8.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from nicegui import app

STORAGE_KEY = "rate_limit_attempts"


def check_and_record(
    bucket: str, key: str, *, limit: int, window: timedelta
) -> tuple[bool, int, timedelta | None]:
    """Checks whether another attempt is allowed for (bucket, key) and, if so,
    records it immediately.

    `bucket` groups the counter by action type (e.g. "discord_refresh"); `key`
    scopes it further (e.g. the target account_id) so the same acting user
    gets an independent allowance per target.

    Returns (allowed, remaining_after_this_call, retry_after). When not
    allowed, remaining is 0 and retry_after is how long until the oldest
    attempt in the window falls out of it.
    """
    all_attempts: dict = app.storage.user.get(STORAGE_KEY, {})
    bucket_attempts: dict = all_attempts.get(bucket, {})
    timestamps = [datetime.fromisoformat(ts) for ts in bucket_attempts.get(key, [])]

    now = datetime.utcnow()
    cutoff = now - window
    timestamps = [ts for ts in timestamps if ts > cutoff]

    if len(timestamps) >= limit:
        retry_after = (timestamps[0] + window) - now
        bucket_attempts[key] = [ts.isoformat() for ts in timestamps]
        all_attempts[bucket] = bucket_attempts
        app.storage.user[STORAGE_KEY] = all_attempts
        return False, 0, retry_after

    timestamps.append(now)
    bucket_attempts[key] = [ts.isoformat() for ts in timestamps]
    all_attempts[bucket] = bucket_attempts
    app.storage.user[STORAGE_KEY] = all_attempts
    return True, limit - len(timestamps), None
