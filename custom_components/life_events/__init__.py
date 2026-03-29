"""The Life Events integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, COORDINATOR
from .coordinator import LifeEventsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

CARD_URL = "/life_events/life-events-card.js"
CARD_FILE = Path(__file__).parent / "life-events-card.js"


async def _register_card(hass: HomeAssistant) -> None:
    """Register the lovelace card static path and inject it into the frontend."""
    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False),
        ])
    except Exception:  # noqa: BLE001 — already registered, safe to ignore
        pass
    add_extra_js_url(hass, CARD_URL)
    _LOGGER.debug("Registered Life Events card at %s", CARD_URL)


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register the lovelace card early, before any config entries are loaded."""
    await _register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Life Events from a config entry."""

    # Also register here so quick restarts (which re-run async_setup_entry
    # without a full async_setup) don't lose the card resource.
    await _register_card(hass)

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
