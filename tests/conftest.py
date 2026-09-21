"""
Test setup.

Every test gets its OWN freshly seeded SQLite database in a temp directory, so tests never touch the
real kingshot.db and can't affect each other. NiceGUI's per-browser session files go to a temp
directory too (NICEGUI_STORAGE_PATH must be set before nicegui is imported), so the real `.nicegui/`
is left alone.

Page tests use NiceGUI's `user` fixture (a simulated browser). It resets the route table for every
test, so each page test module re-imports the page modules it needs in an autouse `routes` fixture.
"""
import os
import tempfile

os.environ["NICEGUI_STORAGE_PATH"] = tempfile.mkdtemp(prefix="ks-nicegui-storage-")

import importlib  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import event as sa_event  # noqa: E402
from sqlmodel import create_engine  # noqa: E402

import app.db as app_db  # noqa: E402
from app.models.schema import Role  # noqa: E402

pytest_plugins = ["nicegui.testing.user_plugin"]


def make_engine(path):
    """A SQLite engine with the app's foreign-key PRAGMA, like the real one in app/db.py."""
    engine = create_engine(f"sqlite:///{path}")
    sa_event.listen(engine, "connect", app_db.enable_foreign_keys)
    return engine


# Safety net: even before any test runs (or if one bypasses the fixture below), nothing can reach the real kingshot.db.
app_db.engine = make_engine(os.path.join(tempfile.mkdtemp(prefix="ks-test-db-"), "unused.db"))


def seed_preview_data() -> None:
    """The four preview seeds, in the order their foreign keys require."""
    from scripts import (
        seed_preview_accounts, seed_preview_events_time_slots, seed_preview_kingdoms_alliances, seed_preview_players,
    )
    seed_preview_accounts.seed()
    seed_preview_kingdoms_alliances.seed()
    seed_preview_players.seed()
    seed_preview_events_time_slots.seed()


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """A fresh, seeded database for this test (accounts 1001-1005, kingdoms 4001-4002, alliances 2001-2006,
    players 3001-3012, events 5001-5007, time slots 6001-6016). No time zones are seeded - tests that
    need some insert their own."""
    engine = make_engine(tmp_path / "test.db")
    monkeypatch.setattr(app_db, "engine", engine)
    seed_preview_data()
    yield
    engine.dispose()


@pytest.fixture
def as_super_admin(monkeypatch):
    """Act as the SuperAdmin preview role (the acting account is the first one, 1001)."""
    role_switcher = importlib.import_module("app.components.role_switcher")
    monkeypatch.setattr(role_switcher, "current_role", lambda: Role.SUPER_ADMIN)
