# app/pages/auth.py

## Purpose
Account registration with real Discord OAuth2 (identify scope, no guild check). Guild membership is checked later, when a player is
added.

## Routes
- `/register` - "Login with Discord": stores a CSRF `state` and redirects to Discord.
- `/auth/discord/callback` - a plain FastAPI route (registered by `register_fastapi_routes()` from `main.py`). It validates the state,
  exchanges the code, fetches the identity and stores it (plus the tokens) in `app.storage.user`. On success it redirects to
  `/register/complete` - or back to `/setup` in setup mode - with `?authorized=1`. On any failure or "Cancel" it redirects back to where
  the login started with `?error=...`.
- `/register/complete` - collects the account's time zone and creates the account. Like the wizard, it only trusts the pending
  identity right after the round trip.

## Shared pieces
- Session keys: `oauth_state`, `setup_mode`, `pending_discord_user`, `pending_discord_token`.
- `discord_account_fields(discord_user, token_data)` maps a Discord identity and token response to the `account` columns; the wizard
  and `/register/complete` share it.

See [../auth/discord_oauth.md](../auth/discord_oauth.md).
