"""
One-time seed for the role-switcher's preview accounts.

Phase 3 of the SQLite migration (see app/models/schema.py's module docstring)
moves Account off app/models/sample_data.py and onto the real `account` table.
That leaves a fresh database with nothing to preview role-gated UI against
except whichever SuperAdmin you created via /setup - scripts/preview_accounts.yaml
holds the same five test accounts sample_data.py used to seed in memory
(gskluzacek_test, marla_singer_2026_test, tyler_durden_58_test, mr_roboto_1983,
max_manual_planck), inserted here for real so role_switcher.py's "Previewing
as" dropdown has something to show.

Explicit account_id values (1001-1005, rather than left to autoincrement) so
that app/models/sample_data.py's still-not-migrated `players` list can
reference them by a fixed, known account_id instead of an `accounts[N].id`
lookup into a list that no longer exists.

Safe to run more than once - skips any account_name that's already present
(same idempotency approach as app/data/time_zones.py's bulk_create_time_zones).

Run from the repo root: `uv run python -m scripts.seed_preview_accounts`
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from sqlmodel import select

from app.db import get_session, init_db
from app.models.schema import Account, AccountType

PREVIEW_ACCOUNTS_PATH = Path(__file__).with_name("preview_accounts.yaml")


def _load_preview_accounts() -> list[dict]:
    rows = yaml.safe_load(PREVIEW_ACCOUNTS_PATH.read_text())
    return [{**row, "account_type": AccountType(row["account_type"])} for row in rows]


def seed() -> None:
    init_db()
    preview_accounts = _load_preview_accounts()
    with get_session() as session:
        existing_names = set(session.exec(select(Account.account_name)))
        now = datetime.utcnow()
        inserted = 0
        for fields in preview_accounts:
            if fields["account_name"] in existing_names:
                continue
            session.add(Account(created_at=now, updated_at=now, **fields))
            inserted += 1
        session.commit()
    skipped = len(preview_accounts) - inserted
    print(f"Inserted {inserted} preview account(s)." + (f" ({skipped} already present, skipped.)" if skipped else ""))


if __name__ == "__main__":
    seed()
