# app/pages/setup.py

## Purpose
The first-run setup wizard at `/setup`. `SetupGateMiddleware` sends the real pages here until the first account exists.

## Steps (a vertical `ui.stepper`)
1. **Time Zones** - upload a CSV with `region,location` columns (`assets/timezone_regions_locations.csv` is one). Rows already
   loaded are skipped; "Next" is refused until at least one zone exists.
2. **Admin Account** - "Continue with Discord" runs the normal OAuth flow (see [auth.md](auth.md)) in setup mode; on return, the
   wizard asks for the account's time zone and creates the account with `is_super_admin=True`. Once the account exists, this step
   just says so.
3. **Kingdoms & Alliances** - a "coming soon" stub; kingdoms and alliances are added from Site Maintenance after setup.

## Details worth knowing
- A pending Discord identity is trusted only immediately after the OAuth round trip (`?authorized=1`); any other load of the page
  clears it, so a stale browser cookie can't resurrect an old login after the database was wiped.
- Several guards stop a second SuperAdmin being created from a stale render of step 2 (the buttons re-check
  `has_any_account()`), backed by the unique constraints on `account`.
