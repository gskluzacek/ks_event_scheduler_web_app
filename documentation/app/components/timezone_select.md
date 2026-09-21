# app/components/timezone_select.py

## Purpose
`TimeZoneSelector(zones, value=None)` renders two cascading dropdowns - Region, then Location filtered by that region -
plus a "Current offset" hint, so users pick a time zone without one very long list.

## Notes
- The caller passes the zones (real `time_zone` rows); the component doesn't fetch anything.
- `.value` is the combined `Region/Location` IANA name, or `None` until both are chosen.
- Both dropdowns are `safe_select`s, so an account's saved zone that no longer exists in the table leaves them empty instead
  of failing.
- Used by the setup wizard, account registration, and the account add/edit dialogs.
