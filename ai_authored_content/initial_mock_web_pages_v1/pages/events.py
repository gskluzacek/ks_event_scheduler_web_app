from __future__ import annotations

from nicegui import ui

from components import layout, role_switcher
from models.sample_data import alliances, events
from models.schema import Event, Role, next_id


@ui.page("/events")
def events_page() -> None:
    ui.page_title("Events - Kingshot Scheduler")
    with layout.frame("/events"):
        can_manage = role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN)
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Events").classes("text-2xl font-bold")
            if can_manage:
                ui.button("Create Event", icon="add", on_click=_open_add_dialog) \
                    .props("unelevated color=primary")
        event_list()


@ui.refreshable
def event_list() -> None:
    can_manage = role_switcher.is_at_least(Role.SCHEDULER_ADMIN, Role.POWER_ADMIN)
    for event in events:
        alliance = next((a.name for a in alliances if a.id == event.alliance_id), "?")
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(event.name).classes("text-lg font-semibold")
                    ui.label(f"{alliance} — {event.description}").classes("text-sm text-grey-6")
                    if event.scheduled_start:
                        ui.label(f"Scheduled: {event.scheduled_start.strftime('%Y-%m-%d %H:%M UTC')}") \
                            .classes("text-sm")
                with ui.row().classes("items-center gap-2"):
                    ui.badge("Published" if event.is_published else "Draft",
                              color="positive" if event.is_published else "grey")
                    if can_manage:
                        ui.button(icon="publish" if not event.is_published else "unpublished",
                                   on_click=lambda e=event: _toggle_publish(e)).props("flat dense round")
                        ui.button(icon="auto_awesome",
                                   on_click=lambda: ui.notify("Scheduling algorithm not implemented in mock",
                                                               type="info")).props("flat dense round") \
                            .tooltip("Run scheduling algorithm")


def _toggle_publish(event: Event) -> None:
    event.is_published = not event.is_published
    event_list.refresh()


def _open_add_dialog() -> None:
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Create Event").classes("text-lg font-bold")
        name = ui.input("Name").props("outlined").classes("w-full")
        description = ui.textarea("Description").props("outlined").classes("w-full")
        alliance_select = ui.select(
            {a.id: a.name for a in alliances}, label="Alliance"
        ).props("outlined").classes("w-full")

        def submit() -> None:
            if not (name.value and alliance_select.value):
                ui.notify("Name and alliance are required", type="warning")
                return
            events.append(Event(
                id=next_id(),
                alliance_id=alliance_select.value,
                name=name.value,
                description=description.value or "",
            ))
            dialog.close()
            event_list.refresh()
            ui.notify("Event created", type="positive")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Create", on_click=submit).props("unelevated color=primary")

    dialog.open()
