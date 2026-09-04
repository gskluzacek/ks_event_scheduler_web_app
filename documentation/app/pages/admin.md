# app/pages/admin.py

## Purpose
Implements Site Maintenance page (`/admin`) for SuperAdmin users, including Kingdom/Alliance and Time Zone maintenance panels.

## Web Features and NiceGUI Usage
NiceGUI patterns used:
- route-level access check and gated rendering.
- tabbed UI (`ui.tabs`, `ui.tab_panels`) to separate maintenance domains.
- `@ui.refreshable` panels for partial updates after create actions.
- modal dialogs for adding kingdoms, alliances, and time zones.

Feature highlights:
- view existing kingdoms and nested alliances
- create kingdom and alliance records
- list time zones with computed UTC offset
- create time zone records

## User Interaction Processing Logic
Interaction flows:
1. Access check:
   - if not SuperAdmin, show access-required message and stop rendering.
2. Kingdom panel:
   - Add Kingdom opens dialog and appends `Kingdom`.
   - Add Alliance per kingdom opens dialog and appends `Alliance`.
   - panel refreshes after create operations.
3. Time zone panel:
   - Add Time Zone opens dialog and appends `TimeZone`.
   - panel table refreshes immediately.

## Current Limitations
- No edit or delete operations for any maintained entity.
- No uniqueness validation (duplicate kingdom names, duplicate guild IDs, duplicate time zones).
- No audit trail or change history.
- Data is still volatile in-memory mock state.

## Existing Issues
1. Data integrity issue:
   - Missing validation can create duplicates and ambiguous lookup behavior.
2. Authorization architecture issue:
   - UI gating depends on role preview state, not hardened backend authorization.
3. UX issue:
   - Silent early return in some submit handlers (missing required fields) gives no feedback in all cases.

## Suggested Improvements
- Add edit/delete and duplicate detection.
- Enforce guild ID constraints and timezone uniqueness.
- Move write operations into validated service layer.
