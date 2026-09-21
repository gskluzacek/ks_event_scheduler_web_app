# app/pages/dashboard.py

## Purpose
`/dashboard`: a welcome line ("previewing as <role>") and summary numbers.

## Content
- Stat cards: **Accounts**, **Players**, **Open Time Slots** and **Events** - each a count read from the database.
- **Upcoming Events**: the event names with a Published/Draft badge.

## Notes
The Published/Draft badge comes from the temporary `event.is_published` column, planned for removal.
