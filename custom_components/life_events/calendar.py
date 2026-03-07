"""Calendar platform for Life Events."""
from __future__ import annotations

import logging
from datetime import date, datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, COORDINATOR, CALENDAR_NAME
from .coordinator import LifeEventsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Life Events calendar."""
    coordinator: LifeEventsCoordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    async_add_entities([LifeEventsCalendar(coordinator, entry)], True)


class LifeEventsCalendar(CoordinatorEntity, CalendarEntity):
    """A calendar entity showing all upcoming life events."""

    _attr_has_entity_name = False
    _attr_name = CALENDAR_NAME

    def __init__(self, coordinator: LifeEventsCoordinator, entry: ConfigEntry) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Life Events",
            manufacturer="Life Events",
            model="Life Events Integration",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event (today or soonest future)."""
        today = date.today()
        events = self.coordinator.get_calendar_events(today, today.replace(year=today.year + 1))
        if not events:
            return None
        ev = events[0]
        return CalendarEvent(
            summary=ev["summary"],
            start=ev["start"],
            end=ev["end"],
            description=ev.get("description", ""),
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return all events in the given date range."""
        raw = self.coordinator.get_calendar_events(start_date.date(), end_date.date())
        return [
            CalendarEvent(
                summary=ev["summary"],
                start=ev["start"],
                end=ev["end"],
                description=ev.get("description", ""),
            )
            for ev in raw
        ]
