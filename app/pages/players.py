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
from app.utils.filters import get_id_filter, get_text_filter, set_filter

FILTER_KINGDOM_KEY = "players_filter_kingdom_id"
FILTER_ALLIANCE_KEY = "players_filter_alliance_id"
FILTER_NAME_KEY = "players_filter_name"


def _visible_players() -> list[Player]:
    role = role_switcher.current_role()
    if role_switcher.is_at_least(Role.ADMIN, Role.POWER_ADMIN):
        return players
    account_id = role_switcher.current_account_id()
    return [p for p in players if p.account_id == account_id]


def _filtered_players() -> list[Player]:
    rows = _visible_players()
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, {k.id for k in kingdoms})
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, {a.id for a in alliances})
    name = get_text_filter(FILTER_NAME_KEY).strip().lower()

    if kingdom_id is not None:
        alliance_ids = {a.id for a in alliances if a.kingdom_id == kingdom_id}
        rows = [p for p in rows if p.alliance_id in alliance_ids]
    if alliance_id is not None:
        rows = [p for p in rows if p.alliance_id == alliance_id]
    if name:
        rows = [p for p in rows if name in p.kingshot_name.lower()]
    return rows


@ui.page("/players")
def players_page() -> None:
    ui.page_title("Players - Kingshot Scheduler")
    with layout.frame("/players"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Player Management").classes("text-2xl font-bold")
            ui.button("Add Player", icon="add", on_click=lambda: _open_add_player_dialog()) \
                .props("unelevated color=primary")

        player_filters()
        player_table()


@ui.refreshable
def player_filters() -> None:
    kingdom_id = get_id_filter(FILTER_KINGDOM_KEY, {k.id for k in kingdoms})
    alliance_id = get_id_filter(FILTER_ALLIANCE_KEY, {a.id for a in alliances})
    name = get_text_filter(FILTER_NAME_KEY)

    with ui.row().classes("w-full items-end gap-2"):
        kingdom_select = ui.select(
            {k.id: k.name for k in kingdoms}, label="Kingdom", value=kingdom_id,
        ).props("outlined dense clearable").classes("w-48")

        # Alliance options are constrained to the currently-selected kingdom, same
        # cascading pattern as the Add Player dialog.
        alliance_options = {
            a.id: a.name for a in alliances if kingdom_id is None or a.kingdom_id == kingdom_id
        }
        alliance_select = ui.select(
            alliance_options, label="Alliance", value=alliance_id,
        ).props("outlined dense clearable").classes("w-48")

        name_input = ui.input("Search Kingshot Name", value=name) \
            .props("outlined dense clearable").classes("w-56")

        def on_kingdom_change() -> None:
            set_filter(FILTER_KINGDOM_KEY, kingdom_select.value)
            # A kingdom change can orphan an already-selected alliance from a
            # different kingdom, so clear it and rebuild the alliance dropdown.
            set_filter(FILTER_ALLIANCE_KEY, None)
            player_filters.refresh()
            player_table.refresh()

        def on_alliance_change() -> None:
            set_filter(FILTER_ALLIANCE_KEY, alliance_select.value)
            player_table.refresh()

        def on_name_change() -> None:
            set_filter(FILTER_NAME_KEY, name_input.value or "")
            player_table.refresh()

        kingdom_select.on_value_change(on_kingdom_change)
        alliance_select.on_value_change(on_alliance_change)
        name_input.on_value_change(on_name_change)

        if kingdom_id is not None or alliance_id is not None or name:
            ui.button("Clear Filters", icon="close", on_click=_clear_player_filters).props("flat dense")


def _clear_player_filters() -> None:
    set_filter(FILTER_KINGDOM_KEY, None)
    set_filter(FILTER_ALLIANCE_KEY, None)
    set_filter(FILTER_NAME_KEY, "")
    player_filters.refresh()
    player_table.refresh()


@ui.refreshable
def player_table() -> None:
    filtered = _filtered_players()
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
        for p in filtered
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
    if not filtered and _visible_players():
        ui.label("No players match the current filters.").classes("text-sm text-grey-5")


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
