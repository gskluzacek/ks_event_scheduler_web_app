# app/pages/dashboard.py

## Purpose
Implements the dashboard route (`/dashboard`) with high-level counts and a quick upcoming-events snapshot.

## Web Features and NiceGUI Usage
NiceGUI usage highlights:
- `@ui.page('/dashboard')` route registration.
- shared wrapper via `layout.frame('/dashboard')`.
- summary cards built with reusable helper `_stat_card(...)`.
- event list rendered with cards and badges.

Displayed features:
- current preview role context label
- aggregate totals for accounts, players, time slots, events
- event publish-state badges

## User Interaction Processing Logic
This page is mostly read-only. Interaction is passive:
- no direct edit dialogs or submit buttons
- updates occur indirectly when other pages mutate in-memory lists and page is reloaded

The route reflects current state derived from shared data collections.

## Current Limitations
- No per-role data scoping: all aggregate counts are global, even for non-admin roles.
- No filtering, sorting, pagination, or drill-down navigation.
- No live updates or auto-refresh timer.

## Existing Issues
1. Authorization/visibility issue:
   - Global counts may expose system-wide metrics to roles that should see subset data.
2. Functional limitation:
   - Event list lacks links/actions to open event details.
3. Product gap:
   - Dashboard does not surface warnings (needs review slots, verification failures, etc.).

## Suggested Improvements
- Scope summary counts by role/account context.
- Add clickable cards for navigation to filtered maintenance pages.
- Add status widgets for operational anomalies.
