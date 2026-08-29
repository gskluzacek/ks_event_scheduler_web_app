from __future__ import annotations

from nicegui import ui

from components import layout, role_switcher
from models.sample_data import accounts
from models.schema import Role


def _visible_accounts():
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return accounts
    return [a for a in accounts if a.id == role_switcher.current_account_id()]


@ui.page("/accounts")
def accounts_page() -> None:
    ui.page_title("Accounts - Kingshot Scheduler")
    with layout.frame("/accounts"):
        ui.label("Account Management").classes("text-2xl font-bold")
        can_manage_others = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)
        if not can_manage_others:
            ui.label("You can view and edit your own account below.").classes("text-grey-6")
        account_table()


@ui.refreshable
def account_table() -> None:
    can_edit = role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN)
    rows = [
        {
            "id": a.id,
            "discord_username": a.discord_username,
            "time_zone": a.time_zone,
            "super_admin": "Yes" if a.is_super_admin else "",
        }
        for a in _visible_accounts()
    ]
    columns = [
        {"name": "discord_username", "label": "Discord User", "field": "discord_username", "sortable": True},
        {"name": "time_zone", "label": "Time Zone", "field": "time_zone", "sortable": True},
        {"name": "super_admin", "label": "SuperAdmin", "field": "super_admin"},
    ]
    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")
    if can_edit:
        table.add_slot(
            "body-cell-discord_username",
            '<q-td><a class="text-primary">{{ props.value }}</a></q-td>',
        )
        ui.label("(Admin/PowerAdmin: click a row in the real app to edit or remove an account)") \
            .classes("text-xs text-grey-5")
