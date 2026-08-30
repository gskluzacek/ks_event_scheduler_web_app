"""
Helper for persisting a sample-data ID in app.storage.user without it being
able to crash the app later.

app.storage.user persists to disk across app restarts (nicegui_llms.md Mental
Model #8), but our mock sample-data IDs come from a single shared counter
(schema.next_id) that gets renumbered whenever sample_data.py changes - e.g.
adding new seeded rows earlier in the file shifts every ID that comes after
them. A stale ID left over from a previous run is not just "wrong data" - if
it's fed straight into something like ui.select(value=stale_id), NiceGUI
raises ValueError and the whole page 500s instead of just ignoring it.

Any time we want to remember a sample-data ID across sessions/restarts
(current preview account, last-viewed event, last-selected player filter,
etc.), route it through get_valid_id() instead of a bare app.storage.user.get()
so a stale value just resets to a sane default rather than crashing.
"""
from __future__ import annotations

from typing import Container, TypeVar

from nicegui import app

T = TypeVar("T")


def get_valid_id(storage_key: str, valid_ids: Container[T], default: T) -> T:
    """Reads `storage_key` from app.storage.user, falling back to `default` if the
    stored value is missing or no longer present in `valid_ids`.

    `valid_ids` should be something re-checkable with `in` (a set, list, or
    similar) - not a one-shot generator, since it may need to be checked more
    than once across the life of a page.
    """
    stored = app.storage.user.get(storage_key)
    if stored in valid_ids:
        return stored
    return default
