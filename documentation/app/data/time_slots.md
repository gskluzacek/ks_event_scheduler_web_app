# app/data/time_slots.py

Repository for `time_slot`. `end_time` is stored as the picked end minus one second (see
[../utils/slot_times.md](../utils/slot_times.md)); this layer stores exactly what it is given.

- `list_time_slots(player_ids=None, event_ids=None)` - ordered by `tslot_id`.
- `get_time_slot(tslot_id)`
- `count_time_slots_by_player(player_ids=None)` - one grouped query, `{player_id: count}`; players with none are absent.
- `create_time_slot(event_id=, player_id=, start_time=, end_time=, tslot_type=PREFERRED, priority=None, confirmed_ind=True, create_account_id=None, update_account_id=None)`
- `update_time_slot(tslot_id, update_account_id=, **fields)`
- `TimeSlotOverlapError` - raised by create/update when the slot would overlap another slot for the same player and event.
  The overlap rule is enforced by two SQLite triggers created with the table (see [../models/schema.md](../models/schema.md)).
