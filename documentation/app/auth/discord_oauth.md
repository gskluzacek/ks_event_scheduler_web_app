# app/auth/discord_oauth.py

## Purpose
Implements Discord OAuth identify-scope helper functions:
- generate CSRF `state`
- build authorize URL
- exchange OAuth code for token
- fetch Discord user profile
- build global avatar CDN URL

The module deliberately does not verify guild membership; that is handled separately.

## Web Features and NiceGUI Usage Context
This file is backend/helper logic used by NiceGUI routes in `app/pages/auth.py`.

NiceGUI-related flow integration:
1. User clicks Login with Discord on a NiceGUI page.
2. Page stores OAuth state in `app.storage.user`.
3. Page redirects to URL built by `build_authorize_url`.
4. FastAPI callback route uses `exchange_code_for_token` and `fetch_discord_user`.
5. NiceGUI page consumes returned identity to complete account registration.

Although this module has no `ui.*` calls, it is central to the auth UI journey.

## User Interaction Processing Logic
Indirect interaction processing occurs via asynchronous network helpers:
- `exchange_code_for_token(code)` handles OAuth code exchange against Discord token endpoint.
- `fetch_discord_user(access_token)` retrieves user identity.
- Errors are surfaced upward and mapped to redirect query params by calling code.

`build_avatar_url` normalizes avatar handling logic for downstream UI components.

## Current Limitations
- Environment variables default to empty strings, allowing misconfiguration to fail late at request time.
- No explicit helper to validate required env vars at import/startup time.
- Timeouts are fixed at 10 seconds with no configuration.
- Uses generic `dict` return types without strong schemas.

## Existing Issues
1. Config safety issue:
   - Empty-string defaults can mask missing secrets until runtime.
2. Type robustness issue:
   - Unstructured `dict` responses increase chance of key errors in callers.
3. Observability issue:
   - No logging/telemetry around OAuth endpoint failures.

## Suggested Improvements
- Add a startup validator for required env vars.
- Introduce typed models (dataclass/pydantic) for token/user payloads.
- Add structured logging for token/user fetch failures.
