"""
Cascading region/location dropdowns that resolve to a full IANA time zone name.

Per web_app_requirements.md > time_zone: a single dropdown of every IANA name
gets unwieldy as the list grows, so instead we pick region first (e.g.
"America"), which narrows a second dropdown to just that region's locations
(e.g. "Chicago"). The full IANA name is the two values joined with "/".

Takes its `zones` as a plain argument rather than importing a fixed list -
callers fetch whatever list is right for them (the real `time_zone` rows) and pass it in, so this component doesn't need to know or care where it
came from.
"""
from __future__ import annotations

from nicegui import ui

from app.components.safe_select import safe_select
from app.models.schema import TimeZone


class TimeZoneSelector:
    """Renders the two selects (call inside the layout where they should appear).

    Usage:
        tz_selector = TimeZoneSelector(zones)
        ...
        iana_name = tz_selector.value  # None until both dropdowns are chosen
    """

    def __init__(self, zones: list[TimeZone], value: str | None = None) -> None:
        self._zones = zones
        regions = sorted({z.region for z in zones})
        initial_region, initial_location = value.split("/", 1) if value else (None, None)

        with ui.row().classes("w-full gap-2"):
            self.region_select = safe_select(
                regions, value=initial_region, label="Region",
            ).props("outlined").classes("flex-1")
            self.location_select = safe_select(
                self._locations_for(initial_region), value=initial_location, label="Location",
            ).props("outlined").classes("flex-1")

        self.offset_label = ui.label().classes("text-xs text-grey-6")

        def on_region_change() -> None:
            self.location_select.set_options(self._locations_for(self.region_select.value))
            self.location_select.value = None
            self._update_offset_label()

        self.region_select.on_value_change(on_region_change)
        self.location_select.on_value_change(self._update_offset_label)
        self._update_offset_label()

    def _locations_for(self, region: str | None) -> list[str]:
        if not region:
            return []
        return sorted(z.location for z in self._zones if z.region == region)

    def _update_offset_label(self) -> None:
        tz = next((z for z in self._zones if z.iana_name == self.value), None)
        self.offset_label.set_text(f"Current offset: {tz.current_utc_offset()}" if tz else "")

    @property
    def value(self) -> str | None:
        """The combined 'Region/Location' IANA name, or None until both are selected."""
        if self.region_select.value and self.location_select.value:
            return f"{self.region_select.value}/{self.location_select.value}"
        return None
