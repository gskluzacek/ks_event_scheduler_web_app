"""
Helper for persisting an ID in app.storage.user without it being able to crash the app later.

app.storage.user persists to disk across app restarts (nicegui_llms.md Mental
Model #8) and outlives the database: the stored value can point at a row that
no longer exists (kingshot.db was deleted and reseeded, which Greg does often
while testing), or, for a filter, at something the current role/viewer can't
see (e.g. an account filter left over from a broader role). A stale ID is not
just "wrong data" - if it's fed straight into something like
ui.select(value=stale_id), NiceGUI raises ValueError and the whole page 500s
instead of just ignoring it.

(This began as a workaround for the old in-memory sample data, whose IDs were
renumbered on every restart. That data is gone, but the guard is still
needed for the reasons above - removing it makes those pages crash again.)

Any time we want to remember an ID across sessions/restarts (current preview
account, a selected filter value, etc.), route it through get_valid_id() instead
of a bare app.storage.user.get() so a stale value just resets to a sane default.
"""
from __future__ import annotations

from typing import Any, Container, TypeVar

from nicegui import app

T = TypeVar("T")


def get_valid_id(
    storage_key: str, valid_ids: Container[T], default: T, storage: dict[str, Any] | None = None
) -> T:
    """Reads `storage_key` from `storage` (app.storage.user by default), falling back to
    `default` if the stored value is missing or no longer present in `valid_ids`.

    `valid_ids` should be something re-checkable with `in` (a set, list, or
    similar) - not a one-shot generator, since it may need to be checked more
    than once across the life of a page.

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
