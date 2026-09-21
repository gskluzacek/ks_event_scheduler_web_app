# app/utils/rate_limit.py

## Purpose
A sliding-window "N attempts per window" limiter kept in `app.storage.user`, so the cap is per acting browser session.

## Contents
`check_and_record(bucket, key, *, limit, window)` returns `(allowed, remaining_after_this_call, retry_after)` and records the
attempt when allowed. `bucket` names the action (for example `discord_refresh`); `key` scopes it (the target account id), so an
admin refreshing another account gets an independent allowance. Timestamps are stored as ISO strings because the storage is
JSON.

## Used by
The Discord "Refresh from Discord" action in `app/pages/accounts.py` (10 per 4 hours).
