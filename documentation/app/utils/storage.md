# app/utils/storage.py

## Purpose
Handling of ids saved in `app.storage.user`, which outlives the data they point at.

## Why a saved id can go stale
A stored id that isn't among a `ui.select`'s options makes NiceGUI raise `ValueError: Invalid value` and the page 500s. That
happens when, for example: another user deletes an event your Event filter still has selected; a role or alliance change
shrinks your visible set; a different person signs in on the same browser; or (development only) `kingshot.db` is deleted and
reseeded, or the preview account/role is switched.

## Layers of defence (all kept)
1. **Development resets**
   - `clear_stored_user_sessions()` deletes NiceGUI's saved sessions (`storage-user-*.json`); `app/main.py` calls it when the
     database was just created.
   - `clear_page_state()` removes the keys starting with `PAGE_STATE_PREFIXES` (`players_`, `timeslots_`) - filters, sort,
     paging, expanded cards - and is called when the preview account/role is switched. It leaves the Discord login-flow keys
     and the rate limiter alone.
2. `get_valid_id(key, valid_ids, default)` - the saved id if it is still among `valid_ids`, else `default`. `valid_ids` is what
   the viewer can pick **now**, not just "rows that exist".
3. [`safe_select()`](../components/safe_select.md) - drops an invalid value at the widget.

## Convention for new code
Use `safe_select()` instead of `ui.select` for any select whose value comes from storage or changing data, and name new
page-state keys `<page>_...` and add the prefix to `PAGE_STATE_PREFIXES`.

## Revisit
This is to be re-evaluated once Greg finishes the per-role, per-screen matrix (`documentation/screen_role_acctions.xlsx`)
and the planned filter revamp.
