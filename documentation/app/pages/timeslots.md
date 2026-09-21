# app/pages/timeslots.py

## Purpose
`/timeslots`: a player's recurring availability windows per event, with filters and View / Add / Edit.

## Visibility (current behavior)
User, Admin and PowerAdmin see only their own account's players' slots. SchedulerAdmin sees slots for players in the alliances their
account's players belong to. SuperAdmin sees everything.

## Table and filters
- Columns: avatar, Player, Event, Local Start, Local End, Type, **Status** (a check mark for confirmed, an x for "needs
  confirmation"). The end shown is the picked end (stored + 1 second), with midnight as `24:00`.
- Filters, left to right: Kingdom and Alliance (SuperAdmin), Account (SchedulerAdmin and SuperAdmin), Player, Event, Type,
  **Status** (OK / Needs Confirmation). The structured ones narrow each other. All are `safe_select`s. Sorting and filters are saved
  per browser.
- The toolbar (View, Edit, Add Time Slot) acts on the selected row; View and Edit are enabled only when exactly one row is selected.

## Dialogs
- **Add**: player, event, start and end hour/minute dropdowns (start 12 AM-11:45 PM in 15-minute steps; **12 AM / 00 as the end
  means midnight**), and type. The status is shown read-only as "Confirmed". The end must be after the start, and the slot can't
  overlap another for the same player and event (a clear warning appears). The creator is null when the owner adds their own slot.
- **Edit**: start, end and type, plus the confirmation control:
  - the **owning account** (even if a SchedulerAdmin/SuperAdmin): confirmed shows read-only "Status: confirmed"; unconfirmed shows a
    "Please confirm" checkbox, and ticking it and saving sets it confirmed. The owner can never unconfirm.
  - a **SchedulerAdmin/SuperAdmin editing someone else's slot**: confirmed shows a "Request confirmation" No/Yes toggle (Yes and save
    sets it unconfirmed); unconfirmed shows read-only "Status: unconfirmed". They can never re-confirm.
- **View**: every column, times shown as picked.

Stored times use the end-minus-one-second convention: see [../utils/slot_times.md](../utils/slot_times.md) and
[../data/time_slots.md](../data/time_slots.md).
