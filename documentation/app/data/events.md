# app/data/events.py

Repository for `event`.

- `list_events(alliance_ids=None)` - ordered by `event_id`
- `get_event(event_id)`
- `create_event(alliance_id=, event_name=, event_desc="", begin_date=None, end_date=None, qty_to_schedule=1, active_ind=True, create_account_id=None)` -
  raises `IntegrityError` if the alliance doesn't exist, the name is used within that alliance, `begin_date` is after
  `end_date`, or `qty_to_schedule < 1`.
- `update_event(event_id, update_account_id=, **fields)`

`scheduled_start`, `scheduled_end` and `is_published` are temporary columns that are planned to be removed.
