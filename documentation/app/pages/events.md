# app/pages/events.py

## Purpose
`/events`: everyone sees the event list; SchedulerAdmin, PowerAdmin and SuperAdmin can also create events and use the publish toggle.

## Content
- Each event card shows the name, the alliance and description, the begin/end window with the quantity to schedule, an "Inactive"
  badge when `active_ind` is false, a "Scheduled:" line when `scheduled_start` is set, and a Published/Draft badge. With no events,
  a "No events yet" note appears.
- Managers also see a publish/unpublish button (saved to the database, recording who changed it) and a placeholder
  "Run scheduling algorithm" button (it only shows a notice; the algorithm isn't built).
- **Create Event** dialog: alliance (from the database), name, description, begin and end date, quantity. The database's rules produce
  friendly messages: a duplicate name within the alliance, a begin date after the end date, a quantity below 1. The creator's account
  id is recorded.

## Notes
`scheduled_start`, `scheduled_end` and `is_published` (and everything above that uses them) are temporary; they are planned to be
removed. The Time Slots page's Event filter and Add dialog list all events, as they always have.
