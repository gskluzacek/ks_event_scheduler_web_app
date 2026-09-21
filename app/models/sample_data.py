"""
The last of the seeded fake data, held in a module-level list.

Every other table is a real SQLite table now (app/data/); only `time_zones` remains here, and
only because admin.py's Time Zones panel still reads and appends to it instead of the real
`time_zone` table. It resets when the app restarts. Once that panel is migrated this file
(and schema.next_id, which only it and that panel use) can be deleted.
"""
from __future__ import annotations

from app.models.schema import TimeZone, next_id

time_zones: list[TimeZone] = [
    TimeZone(timezone_id=next_id(), region="America", location="New_York"),
    TimeZone(timezone_id=next_id(), region="America", location="Chicago"),
    TimeZone(timezone_id=next_id(), region="America", location="Los_Angeles"),
    TimeZone(timezone_id=next_id(), region="Europe", location="London"),
    TimeZone(timezone_id=next_id(), region="Europe", location="Berlin"),
    TimeZone(timezone_id=next_id(), region="Asia", location="Tokyo"),
    TimeZone(timezone_id=next_id(), region="Australia", location="Sydney"),
]
