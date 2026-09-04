# app/utils/filters.py

## Purpose
Centralizes persisted filter and sort helpers for maintenance pages.

## Web Features and NiceGUI Usage Context
This utility supports multiple NiceGUI pages (`accounts`, `players`, `timeslots`) by abstracting:
- reading ID-based filters safely
- reading/writing text filters
- reading/writing table sort state

It is tightly coupled to NiceGUI session storage (`app.storage.user`).

## User Interaction Processing Logic
Typical callback pattern enabled by this file:
1. User changes filter control.
2. Page callback calls `set_filter(...)`.
3. Page rebuild reads values through `get_id_filter(...)` / `get_text_filter(...)`.
4. Invalid stored IDs are auto-healed by `get_valid_id(...)` from storage utility.

Sort behavior:
- table pagination events persist sort-by and descending flags.
- subsequent renders reuse those values.

## Current Limitations
- No namespacing beyond caller-provided keys (collision risk if keys reused).
- Uses session user storage, so values persist broadly across page visits unless cleared.
- No versioning/migration for saved filter key formats.

## Existing Issues
1. Storage coupling issue:
   - Hard dependency on `app.storage.user` may not fit future per-tab/per-view filter requirements.
2. Lifecycle issue:
   - Persisted keys can become stale when data model evolves (partially mitigated for ID filters only).

## Suggested Improvements
- Add key prefix conventions and helper constants.
- Consider optional storage backend parameter for broader reuse.
- Add helper for bulk-clearing namespaced filter keys.
