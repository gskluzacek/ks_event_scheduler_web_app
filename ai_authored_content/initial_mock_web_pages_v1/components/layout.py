"""
Shared page chrome: header, nav, role switcher, content frame.

NiceGUI has no shared "layout template" concept like Jinja base templates -
instead, each @ui.page function calls a shared Python function that builds
the same header/footer elements. Because @ui.page runs its function fresh
per visitor (nicegui_llms.md Mental Model #3), there's no risk of one user's
header leaking into another's.
"""
from __future__ import annotations

from contextlib import contextmanager

from nicegui import ui

from components import role_switcher
from models.schema import Role

# (route, label, icon, roles allowed to SEE the link; None = everyone)
NAV_ITEMS: list[tuple[str, str, str, tuple[Role, ...] | None]] = [
    ("/dashboard", "Dashboard", "space_dashboard", None),
    ("/accounts", "Accounts", "badge", None),
    ("/players", "Players", "groups", None),
    ("/timeslots", "Time Slots", "schedule", None),
    ("/events", "Events", "event", None),
    ("/search", "Search", "search", None),
    ("/admin", "Site Maintenance", "admin_panel_settings", (Role.SUPER_ADMIN,)),
]


@contextmanager
def frame(active_route: str):
    """Wraps a page's content with the shared header/nav and a padded content column.

    Usage:
        @ui.page('/players')
        def players_page():
            with layout.frame('/players'):
                ui.label('Player Management')
    """
    role = role_switcher.current_role()

    with ui.header().classes("items-center justify-between px-4 py-2"):
        with ui.row().classes("items-center gap-6"):
            ui.label("Kingshot Scheduler").classes("text-lg font-bold")
            with ui.row().classes("gap-1"):
                for route, label, icon, allowed_roles in NAV_ITEMS:
                    if allowed_roles and not role_switcher.is_at_least(*allowed_roles):
                        continue
                    is_active = route == active_route
                    btn = ui.button(
                        label, icon=icon, on_click=lambda r=route: ui.navigate.to(r)
                    ).props("flat dense no-caps")
                    if is_active:
                        btn.classes("bg-white/20")
        role_switcher.render()

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        yield
