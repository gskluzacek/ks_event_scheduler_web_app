"""
Helpers for ids persisted in app.storage.user - and for wiping them - so a stored id can't crash a page.

app.storage.user persists to disk across app restarts (nicegui_llms.md Mental Model #8) and outlives
the data it points at. A stored id can go stale in ways that have nothing to do with development:

  - another user DELETES a row the id refers to (e.g. an admin deletes an event that your Event filter
    still has selected; a player or account is removed);
  - a role or scope CHANGES (e.g. a PowerAdmin revokes a role, or a player leaves an alliance, so the
    viewer's visible set shrinks and the alliance/account/player filter they left selected is no
    longer among the choices);
  - a different person signs in on the same browser (the next real-login work), inheriting the last
    person's saved filters;
  - in development only: kingshot.db is deleted and reseeded, or the preview account/role is switched.

A stale id is not just "wrong data" - if it's fed straight into ui.select(value=stale_id), NiceGUI
raises ValueError ("Invalid value") and the whole page 500s instead of just ignoring it.

Layers of defence, from broad to narrow:
  1. Development resets: a brand-new database wipes the saved browser sessions
     (clear_stored_user_sessions(), called from app/main.py), and switching the preview account/role
     wipes the saved page state (clear_page_state(), called from role_switcher).
  2. get_valid_id()/get_id_filter(): the effective value of a stored id, given what this viewer can
     pick right now. The cascading filters use this to compute their current values, so it is
     load-bearing logic, not only a crash guard.
  3. app.components.safe_select.safe_select(): a ui.select that drops a value not among its options.
     Use it instead of ui.select for any select whose value comes from storage or other data that
     may be out of date, so nobody has to remember to call get_valid_id().

TODO (revisit): Greg is drafting documentation/screen_role_acctions.xlsx, the per-role, per-screen matrix of
what can be viewed and done, and plans to revamp the filters. Once that lands, re-evaluate this whole
area (what is persisted, where, and which of these layers are still needed).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Container, TypeVar

from nicegui import app

T = TypeVar("T")

# Session keys holding a page's persisted UI state (filters, sort, paging, expanded cards). Every such
# key must start with one of these prefixes so clear_page_state() finds it - name new ones "<page>_...".
# Deliberately NOT included: the Discord login-flow keys (auth.py) and the refresh rate limiter
# (rate_limit.py) - those aren't UI state and must survive a preview switch.
PAGE_STATE_PREFIXES = ("players_", "timeslots_")


def get_valid_id(
    storage_key: str, valid_ids: Container[T], default: T, storage: dict[str, Any] | None = None
) -> T:
    """Reads `storage_key` from `storage` (app.storage.user by default), falling back to
    `default` if the stored value is missing or no longer present in `valid_ids`.

    `valid_ids` should be something re-checkable with `in` (a set, list, or
    similar) - not a one-shot generator, since it may need to be checked more
    than once across the life of a page.

    `valid_ids` is what the viewer can pick RIGHT NOW, not "every row that exists": a stored id that
    still exists but is out of scope (role changed, alliance left, ...) must be dropped too.

    Pass `storage=app.storage.tab` for values that should reset when the browser tab
    closes but survive navigating between pages within it (e.g. filter selections) -
    see app/utils/filters.py.
    """
    if storage is None:
        storage = app.storage.user
    stored = storage.get(storage_key)
    if stored in valid_ids:
        return stored
    return default


def clear_page_state() -> int:
    """Removes every persisted page-state key (filters, sort, paging, expanded cards) from this
    browser's app.storage.user, so the next page load starts clean. Called when the preview
    account/role is switched (and, later, on real login/logout). Returns how many keys were removed."""
    stale = [key for key in app.storage.user if key.startswith(PAGE_STATE_PREFIXES)]
    for key in stale:
        del app.storage.user[key]
    return len(stale)


def clear_stored_user_sessions(storage_path: Path | None = None) -> int:
    """Deletes NiceGUI's saved per-browser sessions (`storage-user-*.json`) so every browser starts
    with empty app.storage.user. Called at startup when the database was just created: saved ids
    (preview account, filters) would point at rows that no longer exist. Must run before the server
    starts serving. Returns how many files were removed."""
    path = storage_path or Path(os.environ.get("NICEGUI_STORAGE_PATH", ".nicegui")).resolve()
    removed = 0
    for session_file in path.glob("storage-user-*.json"):
        session_file.unlink()
        removed += 1
    return removed
