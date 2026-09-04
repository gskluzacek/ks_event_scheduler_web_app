# app/pages/search.py

## Purpose
Provides a unified search page (`/search`) across accounts, players, and time slots.

## Web Features and NiceGUI Usage
NiceGUI patterns used:
- single `ui.input` with `on_value_change` callback for live filtering
- dynamic result container using `ui.column()` and `results.clear()` rebuilds
- separate render sections using `ui.card()` for Accounts, Players, Time Slots

Feature behavior:
- live search as user types
- if query is empty, accounts/players are displayed broadly
- time slots are rendered only when query has value

## User Interaction Processing Logic
Flow:
1. User types into search input.
2. `run_search()` normalizes text (`lower().strip()`).
3. Results container is cleared and rebuilt.
4. Helper renderers perform in-memory matching:
   - accounts by account name
   - players by kingshot name or kingshot id
   - slots by player name to associated slot records

Role handling is partial:
- `elevated` only controls extra fields in labels.

## Current Limitations
- No paging or performance controls; full list scans on each keypress.
- No debounce/throttle for user input.
- Search scope is inconsistent (time slots match via player names only).
- No advanced criteria (alliance, role, date range, event).

## Existing Issues
1. Data-leakage risk:
   - `accounts` and `players` are searched directly without role-based visibility filtering.
2. Performance issue:
   - O(n) scans with full rebuild on each input event will not scale.
3. UX issue:
   - Empty query floods screen with all accounts/players, which can be noisy.

## Suggested Improvements
- Reuse visibility helpers from maintenance pages to enforce scope.
- Add debounce and pagination.
- Add structured filters alongside text query.
