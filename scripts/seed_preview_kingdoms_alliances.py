"""
One-time seed for the preview kingdoms and alliances (Kingdom/Alliance step of the
SQLite migration).

Run this BEFORE scripts/seed_preview_players.py: `player.alliance_id` is a real
(enforced) foreign key to `alliance`, so the players can't be inserted until the
alliances they belong to exist. scripts/preview_kingdoms_alliances.yaml holds the
two kingdoms and six alliances with fixed ids (4001-4002 and 2001-2006), which
scripts/preview_players.yaml and scripts/preview_events_time_slots.yaml refer to.

Safe to run more than once - skips any kingdom_id / alliance_id already present.

Run from the repo root: `uv run python -m scripts.seed_preview_kingdoms_alliances`
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from sqlmodel import select

from app.db import get_session, init_db
from app.models.schema import Alliance, Kingdom

PREVIEW_PATH = Path(__file__).with_name("preview_kingdoms_alliances.yaml")


def seed() -> None:
    init_db()
    data = yaml.safe_load(PREVIEW_PATH.read_text())
    now = datetime.utcnow()
    with get_session() as session:
        existing_kingdoms = set(session.exec(select(Kingdom.kingdom_id)))
        new_kingdoms = [k for k in data["kingdoms"] if k["kingdom_id"] not in existing_kingdoms]
        session.add_all(Kingdom(created_at=now, updated_at=now, **k) for k in new_kingdoms)
        session.flush()  # kingdoms must exist before the alliances that point at them
        existing_alliances = set(session.exec(select(Alliance.alliance_id)))
        new_alliances = [a for a in data["alliances"] if a["alliance_id"] not in existing_alliances]
        session.add_all(Alliance(created_at=now, updated_at=now, **a) for a in new_alliances)
        session.commit()
    print(f"Inserted {len(new_kingdoms)} kingdom(s) and {len(new_alliances)} alliance(s)."
          + (" (rest already present, skipped.)" if len(new_kingdoms) < len(data["kingdoms"])
             or len(new_alliances) < len(data["alliances"]) else ""))


if __name__ == "__main__":
    seed()
