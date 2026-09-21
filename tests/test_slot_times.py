"""The end-time convention: the stored end is the picked end minus one second (app/utils/slot_times.py)."""
from datetime import time


def test_end_time_conversions():
    from app.utils.slot_times import (end_minutes, format_end_12h, format_end_24h, picked_end_time,
                                      snap_to_quarter_hour, stored_end_time)
    assert stored_end_time(12, 15) == time(12, 14, 59)
    assert stored_end_time(0, 0) == time(23, 59, 59)          # midnight end
    assert stored_end_time(0, 15) == time(0, 14, 59)
    assert picked_end_time(time(12, 14, 59)) == time(12, 15)
    assert picked_end_time(time(23, 59, 59)) == time(0, 0)
    assert format_end_12h(time(17, 14, 59)) == "5:15 PM" and format_end_12h(time(23, 59, 59)) == "12:00 AM (midnight)"
    assert format_end_24h(time(17, 14, 59)) == "17:15" and format_end_24h(time(23, 59, 59)) == "24:00"
    assert end_minutes(0, 0) == 1440 and end_minutes(12, 15) == 735 and snap_to_quarter_hour(59) == 45
    for h in range(24):
        for m in (0, 15, 30, 45):
            assert (picked_end_time(stored_end_time(h, m)).hour, picked_end_time(stored_end_time(h, m)).minute) == (h, m)
