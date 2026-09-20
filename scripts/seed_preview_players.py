"""
One-time seed for the preview players (Phase 4 of the SQLite migration).

Companion to scripts/seed_preview_accounts.py - run that one FIRST, since every
player belongs to one of its accounts (1001-1005). scripts/preview_players.yaml
holds the same twelve players (and their roles) that
app/models/sample_data.py still defines in memory for pages that haven't
migrated yet, with fixed player_id values (3001-3012) so those pages' time
slots keep pointing at the right player.

Safe to run more than once - skips any player_id that's already present.

Run from the repo root: `uv run python -m scripts.seed_preview_players`
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from sqlmodel import select

from app.db import get_session, init_db
from app.models.schema import Account, Player, PlayerRole, Role

PREVIEW_PLAYERS_PATH = Path(__file__).with_name("preview_players.yaml")


def seed() -> None:
    init_db()
    rows = yaml.safe_load(PREVIEW_PLAYERS_PATH.read_text())
    with get_session() as session:
        existing_ids = set(session.exec(select(Player.player_id)))
        missing_accounts = {r["account_id"] for r in rows} - set(session.exec(select(Account.account_id)))
        if missing_accounts:
            raise SystemExit(f"Missing account_id(s) {sorted(missing_accounts)} - run scripts.seed_preview_accounts first.")
        now = datetime.utcnow()
        new_rows = [r for r in rows if r["player_id"] not in existing_ids]
        for row in new_rows:
            fields = {k: v for k, v in row.items() if k != "roles"}
            session.add(Player(created_at=now, updated_at=now, **fields))
            session.add_all(PlayerRole(player_id=row["player_id"], role=Role(r)) for r in row["roles"])
        session.commit()
    skipped = len(rows) - len(new_rows)
    print(f"Inserted {len(new_rows)} preview player(s)." + (f" ({skipped} already present, skipped.)" if skipped else ""))


if __name__ == "__main__":
    seed()
