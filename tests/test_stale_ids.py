"""Stale ids in the browser session (see app/utils/storage.py): the development resets (fresh DB, account/role
switch), safe_select(), and pages surviving ids that no longer exist."""
import asyncio
import importlib
import json
import sys

import pytest
from nicegui import app, ui
from nicegui.testing import User

SELECTS = []  # selects built by the /t_safe test page


@pytest.fixture(autouse=True)
def routes(user: User):
    for name in ("app.pages.players", "app.pages.timeslots", "app.pages.dashboard"):
        sys.modules.pop(name, None)
        importlib.import_module(name)
    SELECTS.clear()
    safe_select = importlib.import_module("app.components.safe_select").safe_select

    @ui.page("/t_seed_state")
    async def _seed():
        for key, value in {
            "players_filter_alliance_id": 99999, "players_filter_kingdom_id": 99999, "players_accounts_page": 3,
            "players_expanded_account_ids": [1, 2], "timeslots_filter_event_id": 99999, "timeslots_sort_by": "player",
            "oauth_state": "keep-me", "setup_mode": True, "pending_discord_user": {"id": "1"},
            "rate_limit_attempts": {"1001": ["2026-09-21T00:00:00"]}, "preview_account_id": 1002, "preview_role": "User",
        }.items():
            app.storage.user[key] = value
        ui.label("seeded")

    @ui.page("/t_dump")
    async def _dump():
        ui.label("KEYS=" + json.dumps(sorted(k for k in app.storage.user if not k.startswith("_"))))

    @ui.page("/t_clear")
    async def _clear():
        from app.utils.storage import clear_page_state
        ui.label(f"cleared={clear_page_state()}")

    @ui.page("/t_stale")
    async def _stale():
        # what a browser looks like after kingshot.db was wiped and reseeded: ids that no longer exist
        app.storage.user["preview_account_id"] = 99999
        app.storage.user["players_filter_alliance_id"] = 99999
        app.storage.user["players_filter_kingdom_id"] = 99999
        ui.label("stale ids stored")

    @ui.page("/t_safe")
    async def _safe():
        SELECTS.extend([
            safe_select({1: "one", 2: "two"}, value=99999, label="stale-dict"),
            safe_select({1: "one", 2: "two"}, value=2, label="valid-dict"),
            safe_select(["a", "b"], value="zzz", label="stale-list"),
            safe_select(["a", "b"], value="b", label="valid-list"),
            safe_select({1: "one"}, label="no-value"),
            safe_select({1: "one", 2: "two"}, value=[2, 99999], multiple=True, label="multi"),
            safe_select({}, value=5, label="empty-options"),
        ])
        ui.label("built")


def keys_on_page(text_labels):
    label = next(t for t in text_labels if t.startswith("KEYS="))
    return set(json.loads(label[len("KEYS="):]))


def labels(user):
    return [e.text for e in user.find(kind=ui.label).elements]


def test_clear_stored_user_sessions_only_removes_user_sessions(tmp_path):
    from app.utils.storage import clear_stored_user_sessions
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    for name in ("storage-user-a.json", "storage-user-b.json", "storage-general.json", "notes.txt"):
        (sessions / name).write_text("{}")
    assert clear_stored_user_sessions(sessions) == 2
    assert sorted(p.name for p in sessions.iterdir()) == ["notes.txt", "storage-general.json"]
    assert clear_stored_user_sessions(sessions) == 0
    assert clear_stored_user_sessions(tmp_path / "does-not-exist") == 0


def test_init_db_reports_whether_it_created_the_database(tmp_path, monkeypatch):
    import app.db as d
    from sqlmodel import create_engine
    monkeypatch.setattr(d, "engine", create_engine(f"sqlite:///{tmp_path / 'fresh.db'}"))
    assert d.init_db() is True          # file did not exist -> created
    assert d.init_db() is False         # second start: already there
    monkeypatch.setattr(d, "engine", create_engine("sqlite:///:memory:"))
    assert d.init_db() is False


async def test_clear_page_state_removes_only_page_state(user: User):
    await user.open("/t_seed_state")
    await user.open("/t_clear")
    await user.should_see("cleared=6")
    await user.open("/t_dump")
    remaining = keys_on_page(labels(user))
    assert remaining >= {"oauth_state", "setup_mode", "pending_discord_user", "rate_limit_attempts",
                         "preview_account_id", "preview_role"}
    assert not [k for k in remaining if k.startswith(("players_", "timeslots_"))]


async def test_switching_role_in_the_header_clears_page_state(user: User):
    await user.open("/t_seed_state")
    await user.open("/dashboard")
    role_select = next(e for e in user.find(kind=ui.select).elements if "SuperAdmin" in e.options)
    role_select.set_value("PowerAdmin")
    await asyncio.sleep(0.5)
    await user.open("/t_dump")
    remaining = keys_on_page(labels(user))
    assert not [k for k in remaining if k.startswith(("players_", "timeslots_"))], remaining
    assert {"oauth_state", "rate_limit_attempts"} <= remaining          # not UI state: untouched
    await user.open("/dashboard")
    assert next(e for e in user.find(kind=ui.select).elements if "SuperAdmin" in e.options).value == "PowerAdmin"


async def test_safe_select_drops_only_values_that_are_not_options(user: User):
    await user.open("/t_safe")
    by_label = {s.props["label"]: s for s in SELECTS}
    assert by_label["stale-dict"].value is None
    assert by_label["valid-dict"].value == 2
    assert by_label["stale-list"].value is None
    assert by_label["valid-list"].value == "b"
    assert by_label["no-value"].value is None
    assert by_label["multi"].value == [2]
    assert by_label["empty-options"].value is None


async def test_pages_survive_stale_ids_even_without_get_valid_id(user: User, monkeypatch):
    """Layer 3 alone: with the get_valid_id() guard disabled, stale ids in storage must not 500 the pages."""
    from app.models.schema import Role
    rs = importlib.import_module("app.components.role_switcher")
    monkeypatch.setattr(rs, "current_role", lambda: Role.SUPER_ADMIN)
    raw = lambda key, valid, default, storage=None: (storage if storage is not None else app.storage.user).get(key, default)
    monkeypatch.setattr(importlib.import_module("app.utils.filters"), "get_valid_id", raw)
    monkeypatch.setattr(rs, "get_valid_id", raw)

    @ui.page("/t_stale2")
    async def _stale():
        for key in ("players_filter_alliance_id", "players_filter_kingdom_id", "timeslots_filter_kingdom_id",
                    "timeslots_filter_alliance_id", "timeslots_filter_account_id", "timeslots_filter_player_id",
                    "timeslots_filter_event_id"):
            app.storage.user[key] = 99999
        app.storage.user["timeslots_filter_type"] = "no-such-type"
        app.storage.user["timeslots_filter_status"] = "no-such-status"
        app.storage.user["preview_account_id"] = 99999
        ui.label("stale")

    await user.open("/t_stale2")
    await user.open("/dashboard")
    await user.should_see("Welcome back")
    await user.open("/players")
    await user.should_see("Account & Player Management")
    await user.open("/timeslots")
    await user.should_see("Time Slot Management")


async def test_pages_survive_stale_ids_in_the_session(user: User, as_super_admin):
    """With the get_valid_id() guard active: the role switcher and filters fall back instead of crashing."""
    await user.open("/t_stale")
    await user.open("/dashboard")          # the role switcher would ui.select(value=99999) without the guard
    await user.should_see("Welcome back")
    await user.open("/players")            # so would the kingdom/alliance filters
    await user.should_see("Account & Player Management")
