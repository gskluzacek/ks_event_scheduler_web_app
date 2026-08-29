"""
Player Management.

The "Add Player" dialog implements the Player Joining Alliance flow from
web_app_requirements.md: pick Kingdom -> Alliance -> Verify Guild Membership
(bot-token check) -> only then can Kingshot player details be entered.
"""
from __future__ import annotations

from nicegui import ui

from app.auth.discord_guild import MembershipResult, verify_guild_membership
from app.components import layout, role_switcher
from app.models.sample_data import accounts, alliances, kingdoms, players
from app.models.schema import Player, Role, next_id


def _visible_players() -> list[Player]:
    role = role_switcher.current_role()
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return players
    account_id = role_switcher.current_account_id()
    return [p for p in players if p.account_id == account_id]


@ui.page("/players")
def players_page() -> None:
    ui.page_title("Players - Kingshot Scheduler")
    with layout.frame("/players"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Player Management").classes("text-2xl font-bold")
            ui.button("Add Player", icon="add", on_click=lambda: _open_add_player_dialog()) \
                .props("unelevated color=primary")

        player_table()


@ui.refreshable
def player_table() -> None:
    rows = [
        {
            "id": p.id,
            "kingshot_name": p.kingshot_name,
            "kingshot_id": p.kingshot_id,
            "alliance": next((a.name for a in alliances if a.id == p.alliance_id), "?"),
            "power": f"{p.power:,}",
            "tc_level": p.town_center_level,
            "roles": ", ".join(r.value for r in p.roles),
        }
        for p in _visible_players()
    ]
    columns = [
        {"name": "kingshot_name", "label": "Name", "field": "kingshot_name", "sortable": True},
        {"name": "kingshot_id", "label": "Kingshot ID", "field": "kingshot_id"},
        {"name": "alliance", "label": "Alliance", "field": "alliance", "sortable": True},
        {"name": "power", "label": "Power", "field": "power", "sortable": True},
        {"name": "tc_level", "label": "TC Lvl", "field": "tc_level", "sortable": True},
        {"name": "roles", "label": "Roles", "field": "roles"},
    ]
    ui.table(columns=columns, rows=rows, row_key="id").classes("w-full").props("flat bordered")


def _open_add_player_dialog() -> None:
    account = next(a for a in accounts if a.id == role_switcher.current_account_id())
    verified_alliance_id: dict[str, int | None] = {"value": None}
    verified_nickname: dict[str, str | None] = {"value": None}

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Add Player").classes("text-lg font-bold")

        kingdom_select = ui.select(
            {k.id: k.name for k in kingdoms}, label="Kingdom"
        ).props("outlined").classes("w-full")
        alliance_select = ui.select({}, label="Alliance").props("outlined").classes("w-full")
        guild_label = ui.label().classes("text-sm text-grey-6")
        verify_status = ui.label().classes("text-sm")

        def on_kingdom_change() -> None:
            options = {a.id: a.name for a in alliances if a.kingdom_id == kingdom_select.value}
            alliance_select.set_options(options)
            alliance_select.value = None
            guild_label.set_text("")
            verify_status.set_text("")
            verified_alliance_id["value"] = None

        def on_alliance_change() -> None:
            alliance = next((a for a in alliances if a.id == alliance_select.value), None)
            guild_label.set_text(f"Discord guild: {alliance.discord_guild_name}" if alliance else "")
            verify_status.set_text("")
            verified_alliance_id["value"] = None

        kingdom_select.on_value_change(on_kingdom_change)
        alliance_select.on_value_change(on_alliance_change)

        async def do_verify() -> None:
            alliance = next((a for a in alliances if a.id == alliance_select.value), None)
            if not alliance:
                ui.notify("Select an alliance first", type="warning")
                return
            verify_status.set_text("Checking membership…")
            check = await verify_guild_membership(alliance.discord_guild_id, account.discord_user_id)
            if check.result == MembershipResult.VERIFIED:
                verified_alliance_id["value"] = alliance.id
                verified_nickname["value"] = check.nickname
                verify_status.classes(remove="text-negative", add="text-positive")
                verify_status.set_text(f"✓ Verified{f' — nick: {check.nickname}' if check.nickname else ''}")
                details_column.set_visibility(True)
            elif check.result == MembershipResult.NOT_A_MEMBER:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ You are not a member of this guild.")
            elif check.result == MembershipResult.BOT_FORBIDDEN:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ Bot credentials are invalid (403).")
            elif check.result == MembershipResult.SERVER_ERROR:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text("✗ Discord returned a server error — bot may have been removed.")
            else:
                verify_status.classes(remove="text-positive", add="text-negative")
                verify_status.set_text(f"✗ Unexpected error: {check.detail}")

        ui.button("Verify Guild Membership", icon="verified_user", on_click=do_verify) \
            .props("outlined")

        with ui.column().classes("w-full gap-2") as details_column:
            kingshot_id = ui.input("Kingshot ID").props("outlined").classes("w-full")
            kingshot_name = ui.input("Kingshot Name").props("outlined").classes("w-full")
            power = ui.number("Power", min=0).props("outlined").classes("w-full")
            tc_level = ui.select(list(range(1, 31)), label="Town Center Level").props("outlined").classes("w-full")
        details_column.set_visibility(False)

        def submit() -> None:
            if not verified_alliance_id["value"]:
                ui.notify("Verify guild membership first", type="warning")
                return
            players.append(Player(
                id=next_id(),
                account_id=account.id,
                alliance_id=verified_alliance_id["value"],
                kingshot_id=kingshot_id.value or "",
                kingshot_name=kingshot_name.value or "",
                discord_nickname=verified_nickname["value"],
                power=int(power.value or 0),
                town_center_level=tc_level.value or 1,
                roles=[Role.USER],
            ))
            dialog.close()
            player_table.refresh()
            ui.notify("Player added", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Add Player", on_click=submit).props("unelevated color=primary")

    dialog.open()
