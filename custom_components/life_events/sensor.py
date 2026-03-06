"""Sensor platform for Life Events."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    COORDINATOR,
    CONF_EVENTS,
    CONF_EVENT_NAME,
    ATTR_NEXT_DATE,
    ATTR_DAYS_UNTIL,
    ATTR_YEARS_AT_NEXT,
    ATTR_EVENT_TYPE,
    ATTR_EVENT_LABEL,
    ATTR_YEAR_UNKNOWN,
    ATTR_ORIGINAL_DATE,
)
from .coordinator import LifeEventsCoordinator, _make_entity_key

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Life Events sensors."""
    coordinator: LifeEventsCoordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    events_config = entry.options.get(CONF_EVENTS, entry.data.get(CONF_EVENTS, []))

    entities = []
    for event in events_config:
        name = event.get(CONF_EVENT_NAME)
        if name:
            entities.append(LifeEventSensor(coordinator, entry, name))

    async_add_entities(entities, True)


class LifeEventSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single life event (days until next occurrence)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "days"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LifeEventsCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self._event_name = name
        self._entity_key = _make_entity_key(name)
        self._entry = entry

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{self._entity_key}"
        self._attr_name = name

    @property
    def _event_data(self) -> dict | None:
        """Return this sensor's data from the coordinator."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._entity_key)

    @property
    def native_value(self) -> int | None:
        """Return days until next occurrence."""
        if data := self._event_data:
            return data.get("days_until")
        return None

    @property
    def icon(self) -> str:
        """Return icon from event data."""
        if data := self._event_data:
            return data.get("icon", "mdi:calendar-star")
        return "mdi:calendar-star"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed event attributes."""
        data = self._event_data
        if not data:
            return {}

        attrs: dict[str, Any] = {
            ATTR_NEXT_DATE: data["next_date"].isoformat() if data.get("next_date") else None,
            ATTR_DAYS_UNTIL: data.get("days_until"),
            ATTR_EVENT_TYPE: data.get("event_type"),
            ATTR_EVENT_LABEL: data.get("event_label"),
            ATTR_YEAR_UNKNOWN: data.get("year_unknown", False),
            ATTR_ORIGINAL_DATE: data.get("original_date"),
        }

        years = data.get("years_at_next")
        if years is not None:
            attrs[ATTR_YEARS_AT_NEXT] = years

        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Group all life event sensors under one device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Life Events",
            manufacturer="Life Events",
            model="Life Events Integration",
            entry_type=DeviceEntryType.SERVICE,
        )
