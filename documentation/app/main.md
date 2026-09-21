# app/main.py

## Purpose
Application entry point. Run from the repository root with `uv run python -m app.main` (the `-m` form is required
because every import is `app.`-prefixed).

## What it does
1. Imports every page module - importing a module is what registers its `@ui.page` routes.
2. Defines `/`, which redirects to `/dashboard`.
3. Calls `init_db()`. If that reports the database file was just created (first run, or `kingshot.db` was deleted),
   it also calls `clear_stored_user_sessions()` so browsers don't keep saved ids (preview account, filters) that point
   at rows that no longer exist.
4. Registers the Discord OAuth callback route (`auth.register_fastapi_routes()`) and adds `SetupGateMiddleware`.
5. Starts the server with `ui.run(title="Kingshot Scheduler", storage_secret=..., reload=True)`.

## Notes / Limitations
- `storage_secret` is hardcoded to `"dev-only-change-me"` rather than read from `STORAGE_SECRET` in `.env`; change this
  before any real deployment.
- A database first created by a seed script (before the app ever starts) is not detected as "new" here; the stale-id
  guards in `app/utils/storage.py` and `app/components/safe_select.py` cover that case.
