# app/pages/auth.py

## Purpose
Implements registration flow pages and Discord OAuth callback route registration:
- `/register`
- `/register/complete`
- FastAPI callback `/auth/discord/callback`

## Web Features and NiceGUI Usage
NiceGUI usage:
- page routes with `@ui.page` for registration UI.
- custom FastAPI route via `@app.get` nested inside `register_fastapi_routes()`.
- session storage (`app.storage.user`) to keep OAuth state and pending Discord user payload.
- component reuse via `TimeZoneSelector`.

Key feature behavior:
- user initiates Discord OAuth from register page
- callback validates CSRF state and exchanges code/token/user profile
- completion page creates account with timezone selection

## User Interaction Processing Logic
Flow breakdown:
1. `/register`:
   - click Login button
   - generate state token
   - store state in session storage
   - redirect to Discord authorize URL
2. Callback:
   - compare returned state with stored state
   - exchange code for token
   - fetch Discord user identity
   - store identity in session as pending registration payload
   - redirect to `/register/complete`
3. `/register/complete`:
   - if no pending payload, show fallback message
   - user selects timezone and submits
   - append new `Account`
   - clear pending state and navigate to dashboard

## Current Limitations
- Sandbox/network constraints prevent live Discord flow testing in this environment.
- No duplicate-account check by Discord user ID.
- No explicit expiration or lifecycle management for pending registration session state.
- No explicit cancellation/reset endpoint.

## Existing Issues
1. Reliability issue:
   - Broad exception capture in callback hides granular failure classification.
2. Data integrity issue:
   - Duplicate account creation is possible for same Discord identity.
3. Security-hardening gap:
   - No additional anti-replay controls beyond single state comparison.

## Suggested Improvements
- Add duplicate-account guard and friendly conflict UX.
- Differentiate callback error reasons for better user support.
- Add cleanup/expiry policy for pending registration state.
