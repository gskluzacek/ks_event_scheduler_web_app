# app/components/timezone_select.py

## Purpose
Provides a reusable cascading timezone selector (Region + Location) that resolves to a full IANA timezone string and displays current UTC offset.

## Web Features and NiceGUI Usage
NiceGUI elements used:
- Two `ui.select` controls in a single responsive `ui.row`.
- An offset `ui.label` updated reactively.
- `on_value_change` handlers for region and location fields.

Usage pattern:
- Instantiate `TimeZoneSelector()` in forms.
- Read `selector.value` to obtain final `Region/Location` string.

## User Interaction Processing Logic
Flow:
1. User selects region.
2. Location options are repopulated dynamically via `_locations_for(region)`.
3. Existing location value is cleared after region change.
4. User selects location.
5. `value` property returns complete IANA name.
6. Offset label updates whenever selection changes.

## Current Limitations
- Data source is in-memory `time_zones`; not database-backed.
- Offset label depends on local timezone conversion helper and may vary by runtime timezone libraries.
- No search/autocomplete for large timezone lists.

## Existing Issues
1. Validation UX issue:
   - If initial provided value is malformed (not `region/location`), split logic can raise.
2. Data coupling issue:
   - Component assumes `time_zones` list shape and uniqueness constraints are valid.

## Suggested Improvements
- Add defensive parsing for malformed initial values.
- Consider searchable selectors for large timezone catalogs.
- Add optional callback hooks for external form validation.
