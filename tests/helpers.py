"""Small helpers shared by the page tests, built on NiceGUI's simulated-browser `User`."""
from __future__ import annotations

import importlib
from datetime import time

from nicegui import ui
from nicegui.testing.user_interaction import UserInteraction

import app.db as app_db
from app.models.schema import Player, Role, TimeSlot, TimeSlotType


def newest(elements, n: int = 1) -> list:
    """The `n` most recently created elements. A rejected submit leaves its dialog open, so a test that
    opens another dialog must target the newest one's fields."""
    return sorted(elements, key=lambda e: e.id)[-n:]


def button(user, text: str, *, last: bool = True) -> UserInteraction:
    """The button whose label is exactly `text` - the newest one (i.e. in the latest dialog) unless last=False."""
    found = sorted((b for b in user.find(kind=ui.button).elements if b.text == text), key=lambda b: b.id)
    assert found, f"no button labelled {text!r}"
    return UserInteraction(user, {found[-1] if last else found[0]}, None)


def icon_buttons(user, icon: str) -> list:
    return sorted((b for b in user.find(kind=ui.button).elements if b.props.get("icon") == icon), key=lambda b: b.id)


def selects(user, label: str, *, in_dialog: bool | None = None) -> list:
    """Every select with this label; `in_dialog` narrows to those inside (True) or outside (False) a dialog."""
    def inside_dialog(element) -> bool:
        while element is not None:
            if isinstance(element, ui.dialog):
                return True
            element = element.parent_slot.parent if getattr(element, "parent_slot", None) else None
        return False

    return [e for e in user.find(kind=ui.select).elements
            if e.props.get("label") == label and (in_dialog is None or inside_dialog(e) == in_dialog)]


def act_as(monkeypatch, role: str, account_id: int) -> None:
    """Pretend the preview switcher is set to this role and account."""
    role_switcher = importlib.import_module("app.components.role_switcher")
    monkeypatch.setattr(role_switcher, "current_role", lambda: Role(role))
    monkeypatch.setattr(role_switcher, "current_account_id", lambda: account_id)


def db():
    return app_db.get_session()


def owner_of(player_id: int) -> int:
    with db() as session:
        return session.get(Player, player_id).account_id


def make_slot(player_id: int, event_id: int, start: time, end: time, *, confirmed: bool = True,
              tslot_type: str = "avoid") -> TimeSlot:
    """Insert a time slot directly (`end` is the STORED end, i.e. the picked end minus one second)."""
    from app.data import time_slots as repo
    return repo._insert(TimeSlot(player_id=player_id, event_id=event_id, start_time=start, end_time=end,
                                 confirmed_ind=confirmed, tslot_type=TimeSlotType(tslot_type)))


def get_slot(tslot_id: int) -> TimeSlot:
    with db() as session:
        return session.get(TimeSlot, tslot_id)
