# app/utils/storage.py

## Purpose
Provides `get_valid_id(...)`, a defensive helper that protects page rendering from stale IDs stored in NiceGUI session storage.

## Web Features and NiceGUI Usage Context
This utility is critical to interaction stability in pages using `ui.select` defaults sourced from persisted state.

Without this guard, stale IDs from previous runs can raise exceptions when select values no longer exist.

## User Interaction Processing Logic
Usage path:
1. Page reads stored value for filter/selection key.
2. Helper checks whether stored value still exists in current valid ID set.
3. Returns stored value if valid; otherwise returns fallback default.

This mechanism allows filters, preview selections, and other persisted IDs to self-heal after seed/data changes.

## Current Limitations
- Only validates membership presence, not semantic correctness of selected value.
- Requires caller to provide current valid ID container and fallback default.
- No logging when fallback correction happens.

## Existing Issues
1. Observability issue:
   - Silent fallback can hide frequent stale-state conditions that merit investigation.
2. API misuse risk:
   - Passing one-shot generators as `valid_ids` may break assumptions (docstring warns, but no runtime enforcement).

## Suggested Improvements
- Add optional debug logging for invalid stored values.
- Add optional type assertions or safer wrappers for valid ID containers.
- Provide helper variants for common storage scopes (`user`, `tab`, `client`).
