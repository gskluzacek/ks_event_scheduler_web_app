# app/main.py

## Purpose
`app/main.py` is the application entry point. It wires route registration by importing page modules, sets up a root redirect, registers FastAPI OAuth callback routes through `app.pages.auth`, and starts NiceGUI.

## Web Features and NiceGUI Usage
Main NiceGUI patterns used:
- `@ui.page('/')` to define the root route.
- `ui.navigate.to('/dashboard')` to redirect from root to dashboard.
- Side-effect route registration by importing page modules:
  - `from app.pages import accounts, admin, auth, dashboard, events, players, search, timeslots`
- `auth.register_fastapi_routes()` to attach custom FastAPI callback endpoints.
- `ui.run(...)` to start NiceGUI server with title and storage settings.

This is a classic NiceGUI multi-page bootstrap style where decorators execute at import-time.

## User Interaction Logic
Interaction is minimal in this file:
1. User visits `/`.
2. `index()` route redirects to `/dashboard`.
3. Actual UI interactions occur in page modules.

The file acts as lifecycle orchestration rather than interaction processing.

## Current Limitations
- `storage_secret` is hardcoded as `dev-only-change-me` rather than sourced from environment variables.
- No explicit host/port configuration in `ui.run(...)`; defaults are used.
- No startup checks for required environment variables.
- No global exception handling layer configured here.

## Existing Issues
1. Security/deployment issue:
   - Hardcoded storage secret in production-capable startup path.
2. Operational issue:
   - Missing explicit environment-driven runtime configuration can lead to drift between environments.
3. Testability issue:
   - Startup behavior is difficult to unit test without refactoring into functions.

## Suggested Improvements
- Read `STORAGE_SECRET` from environment and fail fast if missing in non-dev mode.
- Add optional env-based host/port/reload toggles.
- Wrap startup in callable function to improve integration testing.
