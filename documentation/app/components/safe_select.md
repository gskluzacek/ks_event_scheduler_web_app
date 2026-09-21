# app/components/safe_select.py

## Purpose
`safe_select(options, *, value=None, **kwargs)` builds a `ui.select` but drops a `value` that isn't one of the options,
instead of letting NiceGUI raise `ValueError: Invalid value` (which turns the whole page into a 500).

## When to use it
Instead of `ui.select` for any select whose initial value comes from `app.storage.user` (a saved filter, the preview
account) or from data that may have changed (for example an account's saved time zone that isn't in the `time_zone`
table). It handles dict, list and tuple options and `multiple=True`.

See [../utils/storage.md](../utils/storage.md) for the wider stale-id picture.
