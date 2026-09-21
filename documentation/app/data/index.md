# app/data Documentation Index

One repository module per table. Shared conventions:
- Sync `_private` functions run a query in a short-lived `Session`; the public `async` functions call them through
  `nicegui.run.io_bound`, so pages can simply `await` them.
- There is no in-memory mirror or cache: every call reads or writes exactly what its caller needs.
- Functions that create or update a row take the acting account id and stamp the audit columns
  (`create_account_id`, `created_at`, `update_account_id`, `updated_at`); callers pass
  `role_switcher.current_account_id()`. `create_account_id` is `None` for something a user created for themselves.
- Constraint violations surface as `sqlalchemy.exc.IntegrityError` (the pages turn them into messages), except time
  slot overlaps, which raise `TimeSlotOverlapError`.

- [__init__.md](__init__.md)
- [accounts.md](accounts.md)
- [alliances.md](alliances.md)
- [events.md](events.md)
- [kingdoms.md](kingdoms.md)
- [players.md](players.md)
- [time_slots.md](time_slots.md)
- [time_zones.md](time_zones.md)
