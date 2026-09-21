# app/data/time_zones.py

Repository for `time_zone`.

- `list_time_zones()` - ordered by region, then location.
- `create_time_zone(region=, location=)` - raises `IntegrityError` if the region + location pair already exists.
- `bulk_create_time_zones(rows)` - used by the setup wizard's CSV upload; skips pairs already present (or repeated in the
  batch) and returns how many were inserted.
