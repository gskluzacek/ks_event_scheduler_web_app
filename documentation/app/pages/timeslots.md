# app/pages/timeslots.py

## Purpose
Implements Time Slot Management page (`/timeslots`) with multi-filter controls, sortable table output, and dialog-based time-slot creation.

## Web Features and NiceGUI Usage
NiceGUI patterns used:
- route and shared layout frame
- `@ui.refreshable` filter and table sections
- persisted filters and sort state via utility helpers
- custom avatar table slot for player/account profile display
- dialog form using select/number controls for time slot entry

Feature highlights:
- player, event, type, and needs-review filters
- role-aware slot visibility
- time slot creation with duration-based end-time calculation

## User Interaction Processing Logic
Interaction flow:
1. Page computes visible slot set by role.
2. User applies filters; callback stores value and refreshes table.
3. Table rebuilds row set from filtered results and applies sort state.
4. Add dialog flow:
   - select player and event
   - select hour/minute and duration
   - choose time-slot type
   - submit appends `TimeSlot` and refreshes table

## Current Limitations
- No edit/delete operations.
- No overlap/conflict checks between time slots.
- End time is computed as time-only and does not capture day rollover semantics.
- No alliance scoping checks between selected player and selected event.

## Existing Issues
1. Requirement mismatch issue:
   - Users can create time slots for events outside the player's alliance because event options are not scoped.
2. Validation issue:
   - No guard against duplicate or overlapping windows for same player/event.
3. Data semantics issue:
   - Time-only end values can hide crossing-midnight intent.

## Suggested Improvements
- Restrict event options by selected player's alliance.
- Add conflict/overlap validation.
- Represent overnight windows explicitly or include duration semantics in data model.
