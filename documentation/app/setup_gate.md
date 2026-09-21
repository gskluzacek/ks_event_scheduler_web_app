# app/setup_gate.py

## Purpose
`SetupGateMiddleware` redirects the app's real pages to `/setup` until the first (SuperAdmin) account exists.

## Behavior
- Only the routes in `GATED_ROUTES` (`/` plus every route in `layout.NAV_ITEMS`) are checked. NiceGUI's internal routes,
  `/setup`, `/register*` and the OAuth callback are left alone so the wizard and Discord's redirect back into it always work.
- The check is `accounts.has_any_account()` on each gated request.
