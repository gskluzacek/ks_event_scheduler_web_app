"""Site Maintenance page (/admin): Kingdoms & Alliances and Time Zones panels read/write the DB."""
import asyncio
import importlib
import sys

import pytest
from nicegui import ui
from nicegui.testing import User
from sqlmodel import select

from tests.helpers import button, db


@pytest.fixture(autouse=True)
def routes(user: User):
    sys.modules.pop("app.pages.admin", None)
    importlib.import_module("app.pages.admin")
    # the seeds don't load time zones (the setup wizard does), so give the Time Zones panel a couple
    importlib.import_module("app.data.time_zones")._bulk_insert(
        [{"region": "America", "location": "Chicago"}, {"region": "Europe", "location": "London"}])


def db_names(model, column):
    import app.db as d
    with d.get_session() as s:
        return set(s.exec(select(column)))


async def test_admin_lists_kingdoms_and_alliances(user: User, as_super_admin):
    await user.open("/admin")
    await user.should_see("#1542")
    await user.should_see("[SHD] Shadow Stooges")
    await user.should_see("Dark Lords of the Shadow Realm")


async def test_add_kingdom_and_duplicate(user: User, as_super_admin):
    from app.models.schema import Kingdom
    await user.open("/admin")
    button(user, "Add Kingdom").click()
    user.find("Kingdom Name").type("#7777")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    assert "#7777" in db_names(Kingdom, Kingdom.name)
    await user.should_see("#7777")

    button(user, "Add Kingdom").click()
    user.find("Kingdom Name").type("#7777")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    user.notify.contains("already exists")
    import app.db as d
    with d.get_session() as s:
        assert len(s.exec(select(Kingdom).where(Kingdom.name == "#7777")).all()) == 1


async def test_add_alliance_and_uniqueness(user: User, as_super_admin):
    from app.models.schema import Alliance
    await user.open("/admin")
    button(user, "Add Alliance", last=False).click()   # first kingdom card (#1542, id 4001)
    user.find("Alliance Name").type("[NEW] Brand New")
    user.find("Discord Guild ID").type("111222333")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    import app.db as d
    with d.get_session() as s:
        a = s.exec(select(Alliance).where(Alliance.name == "[NEW] Brand New")).one()
        assert (a.kingdom_id, a.discord_guild_id, a.discord_guild_name, a.create_account_id) == \
               (4001, "111222333", "[NEW] Brand New", 1001), a  # guild name defaults to alliance name
    await user.should_see("[NEW] Brand New")

    # duplicate guild id (belongs to alliance 2002)
    button(user, "Add Alliance", last=False).click()
    user.find("Alliance Name").type("[DUP] Other")
    user.find("Discord Guild ID").type("900000000000002002")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    user.notify.contains("already belongs to another alliance")

    # duplicate name within the same kingdom
    button(user, "Add Alliance", last=False).click()
    user.find("Alliance Name").type("[NEW] Brand New")
    user.find("Discord Guild ID").type("444555666")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    user.notify.contains("already has an alliance named")
    with d.get_session() as s:
        assert len(s.exec(select(Alliance).where(Alliance.name == "[NEW] Brand New")).all()) == 1
        assert not s.exec(select(Alliance).where(Alliance.discord_guild_id.in_(["444555666"]))).all()


def zone_names():
    import app.db as d
    from app.models.schema import TimeZone
    with d.get_session() as s:
        return {f"{z.region}/{z.location}" for z in s.exec(select(TimeZone)).all()}


async def open_tz_tab(user):
    await user.open("/admin")
    user.find("Time Zones").click()
    await asyncio.sleep(0.3)


async def test_panel_lists_db_zones(user: User, as_super_admin):
    await open_tz_tab(user)
    table = sorted(user.find(kind=ui.table).elements, key=lambda e: e.id)[-1]
    listed = {(r["region"], r["location"]) for r in table.rows}
    assert {("America", "Chicago"), ("Europe", "London")} <= listed
    assert all(r["utc_offset"].startswith("UTC") for r in table.rows)
    assert all(isinstance(r["id"], int) for r in table.rows)


async def test_add_time_zone_persists_and_rejects_duplicate_and_blank(user: User, as_super_admin):
    await open_tz_tab(user)
    button(user, "Add Time Zone").click()
    await asyncio.sleep(0.2)
    inputs = sorted((e for e in user.find(kind=ui.input).elements), key=lambda e: e.id)
    region, location = inputs[-2], inputs[-1]
    region.set_value("Asia"); location.set_value(" Kolkata ")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    assert "Asia/Kolkata" in zone_names()                        # trimmed and stored in the real table
    table = sorted(user.find(kind=ui.table).elements, key=lambda e: e.id)[-1]
    assert ("Asia", "Kolkata") in {(r["region"], r["location"]) for r in table.rows}

    button(user, "Add Time Zone").click()
    await asyncio.sleep(0.2)
    inputs = sorted((e for e in user.find(kind=ui.input).elements), key=lambda e: e.id)
    inputs[-2].set_value("Asia"); inputs[-1].set_value("Kolkata")
    button(user, "Add").click()
    await asyncio.sleep(0.5)
    user.notify.contains("already exists")
    assert sum(1 for n in zone_names() if n == "Asia/Kolkata") == 1

    inputs = sorted((e for e in user.find(kind=ui.input).elements), key=lambda e: e.id)
    inputs[-2].set_value(""); inputs[-1].set_value("Nowhere")
    button(user, "Add").click()
    await asyncio.sleep(0.3)
    user.notify.contains("required")
    assert not any(n.endswith("/Nowhere") for n in zone_names())
