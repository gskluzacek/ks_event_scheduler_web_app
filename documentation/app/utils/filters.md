# app/utils/filters.py

## Purpose
Persisted filter and sort state for the page filter rows. Values live in `app.storage.user`, so a filter survives
navigating away and back (and reloads) until the session ends or the state is cleared. (`app.storage.tab` would isolate
filters per browser tab but needs a live websocket connection, which isn't available while a page is being built.)

## Contents
- `get_id_filter(key, valid_ids)` - a stored id, or `None`, dropping it if it isn't in `valid_ids` (what the viewer can pick
  right now). Built on `get_valid_id()`; the cascading Kingdom/Alliance/Account/Player filters rely on it to work out each
  filter's current value.
- `get_text_filter(key)` / `set_filter(key, value)` - text and single-select filters.
- `get_sort_state(by_key, desc_key)` / `set_sort_state(...)` - persisted table sort.

## Conventions
Each page defines its own keys, named `<page>_...` (`players_...`, `timeslots_...`) so `clear_page_state()` can find them
(see [storage.md](storage.md)). Build the selects with [`safe_select`](../components/safe_select.md).
