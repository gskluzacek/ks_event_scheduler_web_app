"""
One-time seed for the preview events and time slots (Event/TimeSlot step of the SQLite migration).

Run this LAST, after scripts/seed_preview_accounts, seed_preview_kingdoms_alliances and
seed_preview_players: events belong to alliances and time slots belong to players and events, all
via enforced foreign keys. scripts/preview_events_time_slots.yaml holds the events (fixed ids 5001-)
and time slots (fixed ids 6001-). Event dates are day offsets from the day this script runs, so a
freshly seeded DB always has current/upcoming events. The no-overlap triggers on `time_slot` apply
here too, so the sample slots are guaranteed not to overlap.

Safe to run more than once - skips any event_id / tslot_id that's already present.

Run from the repo root: `uv run python -m scripts.seed_preview_events_time_slots`
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml
from sqlmodel import select

from app.db import get_session, init_db
from app.models.schema import Alliance, Event, Player, TimeSlot, TimeSlotType

PREVIEW_PATH = Path(__file__).with_name("preview_events_time_slots.yaml")


def _event_from_row(row: dict, today: date, now: datetime) -> Event:
    fields = {k: v for k, v in row.items() if not k.endswith("_offset_days")}
    if "begin_offset_days" in row:
        fields["begin_date"] = today + timedelta(days=row["begin_offset_days"])
    if "end_offset_days" in row:
        fields["end_date"] = today + timedelta(days=row["end_offset_days"])
    if "scheduled_start_offset_days" in row:
        fields["scheduled_start"] = now + timedelta(days=row["scheduled_start_offset_days"])
    return Event(created_at=now, updated_at=now, **fields)


def seed() -> None:
    init_db()
    data = yaml.safe_load(PREVIEW_PATH.read_text())
    today, now = date.today(), datetime.utcnow()
    with get_session() as session:
        missing_alliances = {e["alliance_id"] for e in data["events"]} - set(session.exec(select(Alliance.alliance_id)))
        missing_players = {t["player_id"] for t in data["time_slots"]} - set(session.exec(select(Player.player_id)))
        if missing_alliances or missing_players:
            raise SystemExit(
                f"Missing alliance_id(s) {sorted(missing_alliances)} / player_id(s) {sorted(missing_players)} - run "
                "scripts.seed_preview_kingdoms_alliances and scripts.seed_preview_players first."
            )
        existing_events = set(session.exec(select(Event.event_id)))
        new_events = [e for e in data["events"] if e["event_id"] not in existing_events]
        session.add_all(_event_from_row(e, today, now) for e in new_events)
        session.flush()  # events must exist before the time slots that point at them
        existing_slots = set(session.exec(select(TimeSlot.tslot_id)))
        new_slots = [t for t in data["time_slots"] if t["tslot_id"] not in existing_slots]
        session.add_all(
            TimeSlot(
                created_at=now,
                updated_at=now,
                **{**t, "start_time": time.fromisoformat(t["start_time"]), "end_time": time.fromisoformat(t["end_time"]),
                   "tslot_type": TimeSlotType(t["tslot_type"])},
            )
            for t in new_slots
        )
        session.commit()
    skipped = (len(data["events"]) - len(new_events)) + (len(data["time_slots"]) - len(new_slots))
    print(f"Inserted {len(new_events)} preview event(s) and {len(new_slots)} time slot(s)."
          + (f" ({skipped} already present, skipped.)" if skipped else ""))


if __name__ == "__main__":
    seed()
