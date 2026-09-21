"""
A ui.select that can't crash on an out-of-date value.

NiceGUI's ui.select raises ValueError ("Invalid value") - and the page 500s - if it's given a `value`
that isn't one of its options. Values that come from app.storage.user (a saved filter, the preview
account) or from data that has since changed can be exactly that. Build such selects with safe_select():
it drops a value that isn't among the options (leaving the select empty) instead of raising.

Use it instead of ui.select for any select whose initial value is not guaranteed to be current. See
app/utils/storage.py for the wider picture (and why get_valid_id() still exists alongside this).
"""
from __future__ import annotations

from typing import Any

from nicegui import ui


def safe_select(options: dict | list | tuple, *, value: Any = None, **kwargs: Any) -> ui.select:
    """Same arguments as ui.select (pass everything but `options` and `value` by keyword)."""
    valid = list(options.keys()) if isinstance(options, dict) else list(options)
    if kwargs.get("multiple"):
        value = [v for v in (value or []) if v in valid]
    elif value is not None and value not in valid:
        value = None
    return ui.select(options, value=value, **kwargs)
