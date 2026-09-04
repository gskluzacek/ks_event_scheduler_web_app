# app/models/sample_data.py

## Purpose
Supplies seeded in-memory data used by all pages for mock execution:
- timezone catalog
- kingdoms/alliances
- accounts/players
- events/time slots

## Web Features and NiceGUI Usage Context
NiceGUI pages consume these module-level lists directly to:
- build filter options
- render table/card rows
- append newly created entities
- derive role-based visibility and summary counts

This direct consumption enables rapid prototyping but bypasses a service/repository boundary.

## User Interaction Processing Logic
Most create actions in page callbacks append directly into these lists:
- Account page appends `Account`
- Player page appends `Player`
- Event page appends `Event`
- Time Slot page appends `TimeSlot`
- Admin page appends `Kingdom`, `Alliance`, `TimeZone`

Read actions (filters/searches) iterate lists in-memory on each interaction callback or refresh.

## Current Limitations
- All data is volatile (lost on restart).
- Data is global/shared rather than user-scoped.
- No referential integrity checks beyond ad hoc page logic.
- Seed data includes mock placeholders and values not suitable for production assumptions.

## Existing Issues
1. Data integrity issue:
   - No central guardrails preventing inconsistent test data relationships.
2. UX consistency issue:
   - Some seeded strings and naming conventions are uneven, which can affect demo quality.
3. Scalability issue:
   - Linear scans across large lists will degrade quickly as data volume grows.

## Suggested Improvements
- Move seeded data to fixtures used by tests and seed scripts, not runtime source.
- Introduce repository/service layer APIs.
- Normalize seed naming and enforce stronger sample constraints.
