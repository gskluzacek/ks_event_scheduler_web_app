from __future__ import annotations

from nicegui import ui

from app.components import layout, role_switcher
from app.models.sample_data import accounts, players
from app.models.schema import Role


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
    show_admin_columns = role_switcher.is_any_admin()

    player_count_by_account: dict[int, int] = {}
    for p in players:
        player_count_by_account[p.account_id] = player_count_by_account.get(p.account_id, 0) + 1

    rows = []
    for a in _visible_accounts():
        row = {
            "id": a.id,
            "avatar_url": a.discord_avatar_url,
            "account_name": a.account_name,
            "player_count": player_count_by_account.get(a.id, 0),
            "time_zone": a.time_zone,
        }
        if show_admin_columns:
            row["account_type"] = a.account_type.value
            row["super_admin"] = "Yes" if a.is_super_admin else ""
        rows.append(row)

    columns = [
        {"name": "avatar_url", "label": "", "field": "avatar_url"},
        {"name": "account_name", "label": "Account", "field": "account_name", "sortable": True},
        {"name": "player_count", "label": "Players", "field": "player_count", "sortable": True},
        {"name": "time_zone", "label": "Time Zone", "field": "time_zone", "sortable": True},
    ]
    if show_admin_columns:
        columns.append({"name": "account_type", "label": "Type", "field": "account_type", "sortable": True})
        columns.append({"name": "super_admin", "label": "SuperAdmin", "field": "super_admin"})

    table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")
    # Custom cell: q-avatar with the Discord image if we have one, else a generic icon.
    # ui.table has no Python-level "image column" option, so this is one of the rare
    # legitimate uses of a Quasar template string (nicegui_llms.md > Named Slots).
    table.add_slot(
        "body-cell-avatar_url",
        '''
        <q-td :props="props">
            <q-avatar size="28px" color="grey-4" text-color="grey-8">
                <img v-if="props.value" :src="props.value" style="width: 100%; height: 100%; object-fit: cover" />
                <q-icon v-else name="person" />
            </q-avatar>
        </q-td>
        ''',
    )
    if can_edit:
        table.add_slot(
            "body-cell-account_name",
            '<q-td><a class="text-primary">{{ props.value }}</a></q-td>',
        )
        ui.label("(Admin/PowerAdmin: click a row in the real app to edit or remove an account)") \
            .classes("text-xs text-grey-5")
