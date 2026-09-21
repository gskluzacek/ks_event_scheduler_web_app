# app/pages/admin.py

## Purpose
`/admin` (Site Maintenance), SuperAdmin only - anyone else sees "SuperAdmin access required."

## Tabs
- **Kingdoms & Alliances** - a card per kingdom listing its alliances and their Discord guild. "Add Kingdom" and "Add Alliance"
  (per kingdom) save to the database and record the acting account. Duplicates are rejected by the tables' constraints and reported
  in plain words: a kingdom name already used; an alliance name already used in that kingdom; a Discord guild that already belongs to
  another alliance. Blank fields are ignored and the guild name defaults to the alliance name.
- **Time Zones** - a table of the `time_zone` rows (region, location, current UTC offset, computed for display only) and "Add Time
  Zone"; a duplicate region + location pair is rejected with a message.

## Notes
Add-only for now: there is no edit or delete.
