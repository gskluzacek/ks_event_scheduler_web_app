"""
Persisted filter state for maintenance-page filter rows.

Filters live in app.storage.user (nicegui_llms.md Mental Model #8) - the same
cookie-based, per-browser-session store role_switcher.py already uses for the
account/role preview. That means a filter set on one page is still there if
you navigate away and back, or even reload/restart, until the session cookie
expires.

(app.storage.tab would scope filters more tightly to a single browser tab,
but it requires an active client websocket connection and raises a
RuntimeError if touched during the synchronous part of a @ui.page function -
which is where we read filters to build the initial UI. app.storage.user has
no such restriction, so it's the simpler choice here.)

Usage convention: each page defines its own storage keys (e.g.
"players_filter_kingdom_id") and reads/writes them through the helpers below.
"""
from __future__ import annotations

from typing import Any, Container, TypeVar

from nicegui import app

from app.utils.storage import get_valid_id

T = TypeVar("T")


def get_id_filter(storage_key: str, valid_ids: Container[T]) -> T | None:
    """Dropdown filter holding a sample-data ID (or None = "no filter").

    Reuses get_valid_id()'s staleness guard (app/utils/storage.py) so a filter
    value left over from before a server restart can't crash a ui.select.
    """
    return get_valid_id(storage_key, valid_ids, None, storage=app.storage.user)


def get_text_filter(storage_key: str) -> str:
    """Text/enum-value filter (search boxes, single-select filters keyed by a
    stable string like a TimeSlotType value). Empty string = "no filter".
    """
    return app.storage.user.get(storage_key, "")


def set_filter(storage_key: str, value: Any) -> None:
    app.storage.user[storage_key] = value


def get_sort_state(by_key: str, desc_key: str) -> tuple[str | None, bool]:
    """Persisted table sort (column name + direction), same storage/scope as filters."""
    return app.storage.user.get(by_key), bool(app.storage.user.get(desc_key, False))


def set_sort_state(by_key: str, desc_key: str, sort_by: str | None, descending: bool) -> None:
    app.storage.user[by_key] = sort_by
    app.storage.user[desc_key] = descending

