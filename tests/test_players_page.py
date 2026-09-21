"""Accounts & Players page (/players): filters and dialogs read kingdoms/alliances/slot counts from the DB."""
import asyncio
import importlib
import sys

import pytest
from nicegui import ui
from nicegui.testing import User

from tests.helpers import selects

players = None  # the freshly imported app.pages.players (set by the routes fixture)


@pytest.fixture(autouse=True)
def routes(user: User):
    """The user plugin resets NiceGUI's route table per test, so re-run the @ui.page decorators."""
    global players
    sys.modules.pop("app.pages.players", None)
    players = importlib.import_module("app.pages.players")

    @ui.page("/t_details")
    async def _details_page():
        await players._render_player_details(3001)


async def test_page_renders_and_filters_come_from_db(user: User, as_super_admin):
    await user.open("/players")
    await user.should_see("Account & Player Management")
    await user.should_see("gskluzacek_test")
    kopts = dict(selects(user, "Kingdom")[0].options)
    aopts = dict(selects(user, "Alliance")[0].options)
    print("KOPTS", kopts, "AOPTS", aopts)
    assert kopts == {4001: "#1542", 4002: "#1467"}
    assert set(aopts) <= {2001, 2002, 2003, 2004, 2005, 2006} and 2001 in aopts


async def test_kingdom_filter_narrows_alliances(user: User, as_super_admin):
    await user.open("/players")
    selects(user, "Kingdom")[0].set_value(4001)
    await asyncio.sleep(0.5)  # let the async change handler + filter refresh finish
    names = set(dict(selects(user, "Alliance")[0].options).values())
    print("NARROWED", names)
    assert names and names <= {"[SHD] Shadow Stooges", "[PHX] Dark Phoenix Rising"}


async def test_player_details_show_kingdom_and_alliance(user: User):
    await user.open("/t_details")
    await user.should_see("#1542")
    await user.should_see("[SHD] Shadow Stooges")


async def test_add_player_dialog_cascades(user: User, as_super_admin):
    await user.open("/players")
    user.find("Add Player").click()
    await user.should_see("Verify Guild Membership")
    add_kingdom = selects(user, "Kingdom", in_dialog=True)[0]
    assert dict(add_kingdom.options) == {4001: "#1542", 4002: "#1467"}
    add_kingdom.set_value(4002)
    await asyncio.sleep(0.5)
    names = set(dict(selects(user, "Alliance", in_dialog=True)[0].options).values())
    assert names == {"[UFC] Ultimate Fighting Clan", "[UMP] Umbra Pickles",
                     "[sOS] Hospitable Canteen", "[STN] Silent Thunder and Nonsense"}, names


def test_player_rows_resolve_names():
    from app.data import accounts as ac, alliances as ar, kingdoms as kr, players as pr
    ks, als, rows = kr._list(), ar._list(None), pr._list(None, None)
    accts = {a.account_id: a for a in ac._list()}
    out = {r["id"]: r for r in players._player_rows(
        rows, account_by_id=accts, roles_by_id=None, kingdoms=ks, alliances=als, slot_count_by_player_id={})}
    assert out[3001]["kingdom"] == "#1542" and out[3001]["alliance"] == "[SHD] Shadow Stooges"
    assert all(r["kingdom"] != "?" and r["alliance"] != "?" for r in out.values())


def test_players_page_slot_counts_come_from_db():
    from app.data import accounts as ac, alliances as ar, kingdoms as kr, players as pr, time_slots as tr
    players = importlib.import_module("app.pages.players")
    ks, als, rows = kr._list(), ar._list(None), pr._list(None, None)
    counts = tr._count_by_player(None)
    out = {r["id"]: r for r in players._player_rows(
        rows, account_by_id={a.account_id: a for a in ac._list()}, roles_by_id=None, kingdoms=ks,
        alliances=als, slot_count_by_player_id=counts)}
    assert out[3002]["timeslot_count"] == counts[3002] == 2
    assert all(out[i]["timeslot_count"] == counts.get(i, 0) for i in out)
