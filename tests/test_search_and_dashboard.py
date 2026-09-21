"""Search (/search) and Dashboard (/dashboard) read alliances, events and time slots from the DB."""
import asyncio
import importlib
import sys

import pytest
from nicegui import ui
from nicegui.testing import User
from sqlmodel import select

from tests.helpers import db


@pytest.fixture(autouse=True)
def routes(user: User):
    for name in ("app.pages.search", "app.pages.dashboard"):
        sys.modules.pop(name, None)
        importlib.import_module(name)


async def test_search_shows_alliance_names(user: User):
    await user.open("/search")
    await user.should_see("[SHD] Shadow Stooges")
    await user.should_see("Dark Chocolate")


async def test_search_shows_slots_with_picked_end(user: User):
    await user.open("/search")
    user.find(kind=ui.input).type("dark")
    await asyncio.sleep(0.5)
    await user.should_see("19:00 - 24:00 (preferred)")
    await user.should_see("08:00 - 17:15 (avoid)")


async def test_dashboard_counts_db_slots(user: User):
    from app.models.schema import TimeSlot
    await user.open("/dashboard")
    await user.should_see("Open Time Slots")
    with db() as s:
        total = len(s.exec(select(TimeSlot)).all())
    labels = [e.text for e in user.find(kind=ui.label).elements]
    assert str(total) in labels, (total, labels)


async def test_dashboard_reads_db_events(user: User):
    await user.open("/dashboard")
    await user.should_see("[BT] Bear Hunt")
    await user.should_see("Upcoming Events")
