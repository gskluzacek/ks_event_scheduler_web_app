"""Time Slots page (/timeslots): table, Status filter, and the View/Add/Edit dialogs, including the
confirmed_ind rules, end-minus-one-second times and the no-overlap rule."""
import asyncio
import importlib
import sys
from datetime import time

import pytest
from nicegui import ui
from nicegui.testing import User
from sqlmodel import select

from tests.helpers import act_as, button, db, get_slot, make_slot, newest, owner_of, selects

ts = None  # the freshly imported app.pages.timeslots (set by the routes fixture)


@pytest.fixture(autouse=True)
def routes(user: User):
    """The user plugin resets NiceGUI's route table per test, so re-run the @ui.page decorators."""
    global ts
    sys.modules.pop("app.pages.timeslots", None)
    ts = importlib.import_module("app.pages.timeslots")
    layout = importlib.import_module("app.components.layout")
    time_slots = importlib.import_module("app.data.time_slots")

    @ui.page("/t_edit/{tslot_id}")
    async def _edit_page(tslot_id: int):
        async with layout.frame("/timeslots"):
            await ts._open_edit_slot_dialog(await time_slots.get_time_slot(tslot_id))

    @ui.page("/t_view/{tslot_id}")
    async def _view_page(tslot_id: int):
        async with layout.frame("/timeslots"):
            await ts._render_slot_details(await time_slots.get_time_slot(tslot_id))


async def test_filters_come_from_db(user: User, as_super_admin):
    await user.open("/timeslots")
    await user.should_see("Time Slot Management")
    kopts = dict(selects(user, "Kingdom")[0].options)
    aopts = dict(selects(user, "Alliance")[0].options)
    print("KOPTS", kopts, "AOPTS", aopts)
    assert kopts == {4001: "#1542", 4002: "#1467"}
    assert 2001 in aopts and aopts[2001] == "[SHD] Shadow Stooges"


async def test_kingdom_filter_narrows_alliances(user: User, as_super_admin):
    await user.open("/timeslots")
    selects(user, "Kingdom")[0].set_value(4001)
    await asyncio.sleep(0.5)
    names = set(dict(selects(user, "Alliance")[0].options).values())
    print("NARROWED", names)
    assert names and names <= {"[SHD] Shadow Stooges", "[PHX] Dark Phoenix Rising"}


async def test_table_status_column_and_end_display(user: User, as_super_admin):
    from app.models.schema import TimeSlot
    await user.open("/timeslots")
    table = newest(user.find(kind=ui.table).elements)[0]
    with db() as s:
        seeded = s.exec(select(TimeSlot)).all()
    assert len(table.rows) == len(seeded)
    by_id = {r["id"]: r for r in table.rows}
    assert by_id[6004]["end"] == "24:00" and by_id[6001]["end"] == "17:15" and by_id[6001]["start"] == "08:00"
    assert {r["id"] for r in table.rows if not r["confirmed"]} == {t.tslot_id for t in seeded if not t.confirmed_ind}
    assert [c["label"] for c in table.columns][-1] == "Status"


async def test_status_filter(user: User, as_super_admin):
    from app.models.schema import TimeSlot
    await user.open("/timeslots")
    status = selects(user, "Status")[0]
    assert dict(status.options) == {"ok": "OK", "needs": "Needs Confirmation"}
    status.set_value("needs")
    await asyncio.sleep(0.5)
    with db() as s:
        unconfirmed = {t.tslot_id for t in s.exec(select(TimeSlot).where(TimeSlot.confirmed_ind == False)).all()}  # noqa: E712
    assert unconfirmed and {r["id"] for r in newest(user.find(kind=ui.table).elements)[0].rows} == unconfirmed
    selects(user, "Status")[0].set_value("ok")
    await asyncio.sleep(0.5)
    assert all(r["confirmed"] for r in newest(user.find(kind=ui.table).elements)[0].rows)


async def test_view_shows_rounded_times_and_status(user: User, as_super_admin):
    await user.open("/t_view/6004")           # 19:00:00 - 23:59:59
    await user.should_see("7:00 PM")
    await user.should_see("12:00 AM (midnight)")
    await user.open("/t_view/6001")           # 08:00:00 - 17:14:59
    await user.should_see("5:15 PM")


async def test_view_shows_alliance(user: User, as_super_admin):
    await user.open("/t_view/6001")
    await user.should_see("[SHD] Shadow Stooges")


async def add_slot(user, player_id, event_id, start, end):
    button(user, "Add Time Slot").click()
    await asyncio.sleep(0.2)
    newest(selects(user, "Player"))[0].set_value(player_id)
    newest(selects(user, "Event"))[0].set_value(event_id)
    sh, sm = newest(selects(user, "Start Hour"))[0], newest(selects(user, "Start Minute"))[0]
    eh, em = newest(selects(user, "End Hour"))[0], newest(selects(user, "End Minute"))[0]
    sh.set_value(start[0]); sm.set_value(start[1]); eh.set_value(end[0]); em.set_value(end[1])
    button(user, "Add").click()
    await asyncio.sleep(0.5)


async def test_add_dialog(user: User, as_super_admin):
    from app.models.schema import TimeSlot
    owner = owner_of(3001)
    assert owner == 1001
    await user.open("/timeslots")
    await add_slot(user, 3001, 5005, (12, 0), (13, 0))            # 12:00 PM - 1:00 PM
    with db() as s:
        rows = s.exec(select(TimeSlot).where(TimeSlot.player_id == 3001, TimeSlot.event_id == 5005)).all()
    assert len(rows) == 1
    r = rows[0]
    assert (r.start_time, r.end_time, r.confirmed_ind) == (time(12, 0), time(12, 59, 59), True)
    assert (r.create_account_id, r.update_account_id) == (None, 1001)          # owner added their own slot
    assert str(r.tslot_type) in ("TimeSlotType.PREFERRED", "preferred")

    await add_slot(user, 3001, 5005, (12, 30), (14, 0))          # overlaps the slot just added
    user.notify.contains("overlaps")
    with db() as s:
        assert len(s.exec(select(TimeSlot).where(TimeSlot.player_id == 3001, TimeSlot.event_id == 5005)).all()) == 1

    await add_slot(user, 3001, 5005, (13, 0), (15, 0))           # adjacent is fine (13:00 starts after 12:59:59)
    await add_slot(user, 3001, 5005, (23, 0), (0, 0))            # 11 PM to midnight -> 23:59:59
    with db() as s:
        stored = {(t.start_time, t.end_time) for t in s.exec(select(TimeSlot).where(
            TimeSlot.player_id == 3001, TimeSlot.event_id == 5005)).all()}
    assert stored == {(time(12, 0), time(12, 59, 59)), (time(13, 0), time(14, 59, 59)), (time(23, 0), time(23, 59, 59))}, stored

    await add_slot(user, 3001, 5006, (14, 0), (14, 0))           # end == start
    user.notify.contains("End time must be after start time")
    await add_slot(user, 3001, 5006, (14, 0), (0, 0))            # 2 PM to midnight is fine
    with db() as s:
        assert len(s.exec(select(TimeSlot).where(TimeSlot.player_id == 3001, TimeSlot.event_id == 5006)).all()) == 1


async def test_add_dialog_shows_read_only_confirmed_status(user: User, as_super_admin):
    await user.open("/timeslots")
    button(user, "Add Time Slot").click()
    await asyncio.sleep(0.2)
    await user.should_see("Confirmed")
    with pytest.raises(AssertionError):
        user.find("Request confirmation")
    with pytest.raises(AssertionError):
        user.find(kind=ui.toggle)            # no toggle for anyone in the Add dialog


async def test_add_for_another_accounts_player_records_creator(user: User, as_super_admin):
    from app.models.schema import TimeSlot
    other = 3009
    assert owner_of(other) != 1001
    await user.open("/timeslots")
    await add_slot(user, other, 5007, (6, 0), (7, 0))
    with db() as s:
        r = s.exec(select(TimeSlot).where(TimeSlot.player_id == other, TimeSlot.event_id == 5007)).one()
    assert (r.create_account_id, r.update_account_id, r.confirmed_ind) == (1001, 1001, True)


async def edit_and_save(user, tslot_id, *, checkbox=None, toggle=None, end=None):
    await user.open(f"/t_edit/{tslot_id}")
    await asyncio.sleep(0.2)
    if checkbox is not None: newest(user.find(kind=ui.checkbox).elements)[0].set_value(checkbox)
    if toggle is not None: newest(user.find(kind=ui.toggle).elements)[0].set_value(toggle)
    if end: newest(selects(user, "End Hour"))[0].set_value(end[0]); newest(selects(user, "End Minute"))[0].set_value(end[1])
    button(user, "Save").click()
    await asyncio.sleep(0.5)
    return get_slot(tslot_id)


async def test_owner_confirms_unconfirmed_slot(user: User, monkeypatch):
    act_as(monkeypatch, "User", 1001)
    slot = make_slot(3001, 5003, time(1, 0), time(1, 14, 59), confirmed=False)
    await user.open(f"/t_edit/{slot.tslot_id}")
    await user.should_see("Please confirm")
    with pytest.raises(AssertionError):
        user.find("Request confirmation")
    after = await edit_and_save(user, slot.tslot_id, checkbox=True)
    assert after.confirmed_ind is True and after.update_account_id == 1001


async def test_owner_leaving_box_unchecked_keeps_unconfirmed(user: User, monkeypatch):
    act_as(monkeypatch, "User", 1001)
    slot = make_slot(3001, 5003, time(2, 0), time(2, 14, 59), confirmed=False)
    after = await edit_and_save(user, slot.tslot_id, checkbox=False, end=(2, 45))   # edit the end, leave unconfirmed
    assert after.confirmed_ind is False and after.end_time == time(2, 44, 59)


async def test_owner_cannot_unconfirm_a_confirmed_slot(user: User, monkeypatch):
    act_as(monkeypatch, "User", 1001)
    slot = make_slot(3001, 5003, time(3, 0), time(3, 14, 59), confirmed=True)
    await user.open(f"/t_edit/{slot.tslot_id}")
    await user.should_see("Confirmed")
    with pytest.raises(AssertionError):
        user.find("Please confirm")
    with pytest.raises(AssertionError):
        user.find("Request confirmation")
    with pytest.raises(AssertionError):
        user.find(kind=ui.checkbox)          # nothing to tick or toggle on a confirmed slot for its owner
    with pytest.raises(AssertionError):
        user.find(kind=ui.toggle)
    after = await edit_and_save(user, slot.tslot_id)
    assert after.confirmed_ind is True


async def test_scheduler_requests_confirmation_on_others_slot(user: User, monkeypatch):
    act_as(monkeypatch, "SchedulerAdmin", 1002)
    assert owner_of(3001) == 1001
    slot = make_slot(3001, 5003, time(4, 0), time(4, 14, 59), confirmed=True)
    await user.open(f"/t_edit/{slot.tslot_id}")
    await user.should_see("Request confirmation")
    with pytest.raises(AssertionError):
        user.find("Please confirm")
    assert (await edit_and_save(user, slot.tslot_id, toggle=False)).confirmed_ind is True        # No -> unchanged
    after = await edit_and_save(user, slot.tslot_id, toggle=True)                                # Yes -> unconfirmed
    assert after.confirmed_ind is False and after.update_account_id == 1002


async def test_scheduler_cannot_reconfirm(user: User, monkeypatch):
    act_as(monkeypatch, "SuperAdmin", 1002)
    slot = make_slot(3001, 5003, time(5, 0), time(5, 14, 59), confirmed=False)
    await user.open(f"/t_edit/{slot.tslot_id}")
    await user.should_see("Unconfirmed")
    with pytest.raises(AssertionError):
        user.find("Request confirmation")
    with pytest.raises(AssertionError):
        user.find("Please confirm")
    assert (await edit_and_save(user, slot.tslot_id)).confirmed_ind is False


async def test_scheduler_who_owns_the_slot_gets_owner_rules(user: User, monkeypatch):
    act_as(monkeypatch, "SuperAdmin", 1001)                # 1001 owns player 3001
    slot = make_slot(3001, 5003, time(6, 0), time(6, 14, 59), confirmed=False)
    await user.open(f"/t_edit/{slot.tslot_id}")
    await user.should_see("Please confirm")                # owner rule: they CAN confirm their own slot
    assert (await edit_and_save(user, slot.tslot_id, checkbox=True)).confirmed_ind is True
    slot2 = make_slot(3001, 5003, time(7, 0), time(7, 14, 59), confirmed=True)
    await user.open(f"/t_edit/{slot2.tslot_id}")
    with pytest.raises(AssertionError):
        user.find("Request confirmation")                 # ...but cannot ask themselves to re-confirm


async def test_edit_shows_picked_end_and_rejects_overlap(user: User, monkeypatch):
    act_as(monkeypatch, "User", 1001)
    a = make_slot(3001, 5004, time(8, 0), time(8, 59, 59))
    b = make_slot(3001, 5004, time(9, 0), time(9, 59, 59))
    await user.open(f"/t_edit/{b.tslot_id}")
    assert newest(selects(user, "End Hour"))[0].value == 10 and newest(selects(user, "End Minute"))[0].value == 0
    after = await edit_and_save(user, b.tslot_id, end=(11, 0))
    assert after.end_time == time(10, 59, 59)
    # move b's start into a: overlap -> rejected, row unchanged
    await user.open(f"/t_edit/{b.tslot_id}")
    newest(selects(user, "Start Hour"))[0].set_value(8); newest(selects(user, "Start Minute"))[0].set_value(30)
    button(user, "Save").click()
    await asyncio.sleep(0.5)
    user.notify.contains("overlaps")
    assert get_slot(b.tslot_id).start_time == time(9, 0)
    # a midnight-ending slot round-trips through the edit dialog as 12 AM / 00
    m = make_slot(3001, 5004, time(22, 0), time(23, 59, 59))
    await user.open(f"/t_edit/{m.tslot_id}")
    assert (newest(selects(user, "End Hour"))[0].value, newest(selects(user, "End Minute"))[0].value) == (0, 0)
