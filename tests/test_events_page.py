"""Events page (/events): list, Create Event dialog, constraints and the publish toggle, all against the DB."""
import asyncio
import importlib
import sys

import pytest
from nicegui import ui
from nicegui.testing import User
from nicegui.testing.user_interaction import UserInteraction
from sqlmodel import select

from tests.helpers import button, icon_buttons, newest


@pytest.fixture(autouse=True)
def routes(user: User):
    sys.modules.pop("app.pages.events", None)
    importlib.import_module("app.pages.events")


def event_by_name(name):
    import app.db as d
    from app.models.schema import Event
    with d.get_session() as s:
        return s.exec(select(Event).where(Event.event_name == name)).all()


async def fill_dialog(user, name, alliance_id, *, begin=None, end=None, qty=None):
    button(user, "Create Event").click()
    await asyncio.sleep(0.2)
    name_input = newest(e for e in user.find(kind=ui.input).elements if e.props.get("label") == "Name")[0]
    name_input.set_value(name)
    sel = newest(e for e in user.find(kind=ui.select).elements if e.props.get("label") == "Alliance")[0]
    assert dict(sel.options)[2001] == "[SHD] Shadow Stooges"   # options come from the DB
    sel.set_value(alliance_id)
    begin_el, end_el = newest(user.find(kind=ui.date).elements, 2)
    if begin: begin_el.set_value(begin)
    if end: end_el.set_value(end)
    if qty: newest(user.find(kind=ui.number).elements)[0].set_value(qty)
    button(user, "Create").click()
    await asyncio.sleep(0.5)


async def test_lists_db_events(user: User):
    await user.open("/events")
    await user.should_see("[BT] Bear Hunt")
    await user.should_see("[SHD] Shadow Stooges — EOD bear trap")
    await user.should_see("Published")          # Bear Hunt is seeded published
    await user.should_see("Scheduled:")         # KvK's temporary scheduled_start still shown


async def test_create_event_and_constraints(user: User, as_super_admin):
    await user.open("/events")
    await fill_dialog(user, "[T2] Step Two", 2001, begin="2026-10-01", end="2026-10-05", qty=3)
    ev, = event_by_name("[T2] Step Two")
    assert (ev.alliance_id, ev.qty_to_schedule, ev.create_account_id, ev.update_account_id, ev.active_ind, ev.is_published) == \
           (2001, 3, 1001, 1001, True, False), ev
    assert str(ev.begin_date) == "2026-10-01" and str(ev.end_date) == "2026-10-05"
    await user.should_see("[T2] Step Two")

    await fill_dialog(user, "[T2] Step Two", 2001)               # same alliance + name
    user.notify.contains("already has an event with this name")
    assert len(event_by_name("[T2] Step Two")) == 1

    await fill_dialog(user, "[T2] Step Two", 2002)               # same name, other alliance: allowed
    assert len(event_by_name("[T2] Step Two")) == 2

    await fill_dialog(user, "[T2] Backwards", 2001, begin="2026-10-09", end="2026-10-01")
    user.notify.contains("begin date can't be after the end date")
    assert not event_by_name("[T2] Backwards")


async def test_toggle_publish_persists(user: User, as_super_admin):
    from app.models.schema import Event
    import app.db as d
    await user.open("/events")
    # a draft event (not published) shows the 'publish' icon; click the first one
    with d.get_session() as s:
        draft = s.exec(select(Event).where(Event.is_published == False).order_by(Event.event_id)).first()  # noqa: E712
    UserInteraction(user, {icon_buttons(user, "publish")[0]}, None).click()
    await asyncio.sleep(0.5)
    with d.get_session() as s:
        after = s.get(Event, draft.event_id)
    assert after.is_published is True and after.update_account_id == 1001, after


async def test_events_page_uses_db_alliances(user: User, as_super_admin):
    await user.open("/events")
    await user.should_see("[SHD] Shadow Stooges")   # "<alliance> — <description>" line
    button(user, "Create Event", last=False).click()
    await asyncio.sleep(0.3)
    sel = [e for e in user.find(kind=ui.select).elements if e.props.get("label") == "Alliance"][0]
    assert 2001 in dict(sel.options) and dict(sel.options)[2001] == "[SHD] Shadow Stooges"
