# app/pages/events.py

## Purpose
Implements Event Management page (`/events`) with list display, publish toggle, and event creation dialog for scheduler-capable roles.

## Web Features and NiceGUI Usage
NiceGUI features used:
- role-gated `Create Event` action button
- `@ui.refreshable` event list for lightweight list refresh after mutations
- card-based event rendering with badges for draft/published/inactive
- modal creation dialog using `ui.dialog` and form inputs
- simple toast notifications via `ui.notify`

Role behavior:
- scheduler and power admin roles can create and publish/unpublish events
- all users can view event list

## User Interaction Processing Logic
Interaction paths:
1. Create flow:
   - user opens dialog
   - enters name/description/alliance/window/quantity
   - submit validates required fields (name + alliance)
   - event appended to in-memory list
   - list refresh + success notification
2. Publish flow:
   - user clicks round publish icon
   - `is_published` toggles
   - event list refreshes
3. Scheduling action:
   - action button currently shows informational notification only

## Current Limitations
- No edit/delete for existing events.
- No server-side validation for date range consistency.
- Scheduling algorithm is stubbed.
- Event visibility is not alliance-scoped for non-admin roles.

## Existing Issues
1. Rules enforcement gap:
   - Users can create events with invalid windows (e.g., end before begin) because no validation exists.
2. Authorization gap:
   - All users can see all events, regardless of alliance context.
3. Functional gap:
   - "Run scheduling algorithm" is non-functional placeholder.

## Suggested Improvements
- Add edit/delete and status transitions.
- Enforce begin/end date validation.
- Implement alliance-scoped visibility and scheduling service.
