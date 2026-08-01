"""The Life Events integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers import entity_registry as er

from .const import CONF_EVENTS, COORDINATOR, DOMAIN
from .coordinator import LifeEventsCoordinator, make_entity_key

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

_CARD_URL_BASE = "/life_events"
_CARD_FILENAME = "life-events-card.js"
_CARD_FILE = Path(__file__).parent / _CARD_FILENAME
_CARD_RESOURCE_URL = f"{_CARD_URL_BASE}/{_CARD_FILENAME}"
_SERVICE_DELETE_EVENTS = "delete_events"


async def _register_card(hass: HomeAssistant) -> None:
    """Serve the JS file and register it as a persistent Lovelace resource."""
    # Serve the file via a static HTTP path.
    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(_CARD_RESOURCE_URL, str(_CARD_FILE), cache_headers=False),
        ])
    except Exception:  # noqa: BLE001 — already registered on quick restarts
        pass

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace not available; skipping resource registration")
        return

    mode = getattr(lovelace, "mode", getattr(lovelace, "resource_mode", "yaml"))
    if mode != "storage":
        _LOGGER.debug("Lovelace in YAML mode; add the resource manually")
        return

    async def _try_register(_now: Any) -> None:
        """Register the resource once Lovelace has loaded its collection from storage."""
        if not lovelace.resources.loaded:
            _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5 s")
            async_call_later(hass, 5, _try_register)
            return

        existing = lovelace.resources.async_items()
        for resource in existing:
            if resource.get("url", "").startswith(_CARD_URL_BASE):
                _LOGGER.debug("Life Events card resource already registered")
                return

        await lovelace.resources.async_create_item({
            "res_type": "module",
            "url": _CARD_RESOURCE_URL,
        })
        _LOGGER.info("Registered Life Events card as Lovelace resource: %s", _CARD_RESOURCE_URL)

    await _try_register(None)


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register the static path early, before config entries are loaded."""
    await _register_card(hass)

    async def _async_delete_events(call: ServiceCall) -> dict[str, int]:
        """Delete selected events and remove their sensor registry entries."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Life Events must be configured before deleting")

        entry = entries[0]
        requested_ids = set(call.data.get("event_ids", []))
        requested_entity_ids = set(call.data.get("entity_ids", []))
        if not requested_ids and not requested_entity_ids:
            raise HomeAssistantError("No Life Events were selected")

        existing = list(
            entry.options.get(CONF_EVENTS, entry.data.get(CONF_EVENTS, []))
        )
        registry = er.async_get(hass)
        matched: list[tuple[dict, str | None]] = []

        for event in existing:
            unique_id = f"{DOMAIN}_{entry.entry_id}_{make_entity_key(event.get('name', ''))}"
            entity_id = registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, unique_id
            )
            if event.get("_id") in requested_ids or entity_id in requested_entity_ids:
                matched.append((event, entity_id))

        if not matched:
            raise HomeAssistantError("No matching Life Events were found")

        matched_objects = {id(event) for event, _entity_id in matched}
        remaining = [event for event in existing if id(event) not in matched_objects]
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_EVENTS: remaining},
        )

        for _event, entity_id in matched:
            if entity_id is not None:
                registry.async_remove(entity_id)

        return {"deleted": len(matched), "total": len(remaining)}

    hass.services.async_register(
        DOMAIN,
        _SERVICE_DELETE_EVENTS,
        _async_delete_events,
        schema=vol.Schema(
            {
                vol.Optional("event_ids", default=[]): [str],
                vol.Optional("entity_ids", default=[]): [str],
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Life Events from a config entry."""
    coordinator = LifeEventsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
