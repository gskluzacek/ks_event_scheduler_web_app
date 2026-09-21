# app/components/layout.py

## Purpose
The shared page chrome: header, navigation links, the preview role switcher and a padded content column. NiceGUI has no
template inheritance, so each page wraps its content in `async with layout.frame(route):`.

## Contents
- `NAV_ITEMS` - `(route, label, icon, roles allowed to see the link)`: Dashboard `/dashboard`, Accounts & Players
  `/players`, Time Slots `/timeslots`, Events `/events`, Search `/search`, and Site Maintenance `/admin` (SuperAdmin only).
  `setup_gate.GATED_ROUTES` is built from this list.
- `frame(active_route)` - an async context manager. It awaits `role_switcher.load_accounts()` once per page load (which is
  why every page function is `async`), adds one CSS rule tinting every table header light blue-gray (`#dbe4ee`), then builds
  the header with the links visible to the current role.

## Notes
Because `@ui.page` builds the page fresh per visitor, one user's header can't leak into another's.
