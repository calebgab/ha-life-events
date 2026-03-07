"""Config flow for Life Events integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_EVENTS,
    CONF_EVENT_NAME,
    CONF_EVENT_DATE,
    CONF_EVENT_TYPE,
    CONF_EVENT_CUSTOM_LABEL,
    CONF_EVENT_ICON,
    CONF_EVENT_YEAR_UNKNOWN,
    EVENT_TYPES,
)

_LOGGER = logging.getLogger(__name__)

# Sentinel for "add new event" selection in the options menu
_ADD_EVENT = "__add__"
_DONE = "__done__"


class LifeEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow (one-time setup)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step — just confirm and create the entry."""
        # Only allow one instance of the integration
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Life Events",
                data={CONF_EVENTS: []},
            )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "description": (
                    "Life Events tracks birthdays, anniversaries, and custom "
                    "recurring dates. After setup, add your events via the "
                    "Configure button on the integration card."
                )
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return LifeEventsOptionsFlow(config_entry)


class LifeEventsOptionsFlow(config_entries.OptionsFlow):
    """Handle the options flow for adding/editing/removing events."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self._events: list[dict] = list(
            config_entry.options.get(
                CONF_EVENTS,
                config_entry.data.get(CONF_EVENTS, []),
            )
        )
        self._editing_index: int | None = None

    # ── Main menu ──────────────────────────────────────────────────────────

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the main event management menu."""
        if user_input is not None:
            selection = user_input.get("action")
            if selection == _ADD_EVENT:
                self._editing_index = None
                return await self.async_step_event_form()
            if selection == _DONE:
                return self.async_create_entry(
                    title="", data={CONF_EVENTS: self._events}
                )
            # User picked an existing event — find its index
            for i, ev in enumerate(self._events):
                if ev.get("_id") == selection:
                    self._editing_index = i
                    return await self.async_step_event_form()

        # Build the select options
        event_options = {
            ev.get("_id", str(i)): _event_summary(ev)
            for i, ev in enumerate(self._events)
        }
        event_options[_ADD_EVENT] = "➕  Add new event"
        event_options[_DONE] = "✅  Save and finish"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required("action"): vol.In(event_options)}
            ),
            description_placeholders={
                "count": str(len(self._events)),
            },
        )

    # ── Add / Edit form ────────────────────────────────────────────────────

    async def async_step_event_form(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Form for creating or editing a single event."""
        errors: dict[str, str] = {}
        existing: dict = {}

        if self._editing_index is not None:
            existing = self._events[self._editing_index]

        if user_input is not None:
            action = user_input.get("_action", "save")

            if action == "delete" and self._editing_index is not None:
                self._events.pop(self._editing_index)
                return await self.async_step_init()

            # Validate date format
            date_str: str = user_input.get(CONF_EVENT_DATE, "")
            year_unknown: bool = user_input.get(CONF_EVENT_YEAR_UNKNOWN, False)

            if not _validate_date(date_str, year_unknown):
                errors[CONF_EVENT_DATE] = "invalid_date"
            else:
                event_data = {
                    "_id": existing.get("_id") or str(uuid.uuid4())[:8],
                    CONF_EVENT_NAME: user_input[CONF_EVENT_NAME].strip(),
                    CONF_EVENT_DATE: date_str.strip(),
                    CONF_EVENT_TYPE: user_input[CONF_EVENT_TYPE],
                    CONF_EVENT_CUSTOM_LABEL: user_input.get(CONF_EVENT_CUSTOM_LABEL, "").strip(),
                    CONF_EVENT_ICON: user_input.get(CONF_EVENT_ICON, "").strip(),
                    CONF_EVENT_YEAR_UNKNOWN: year_unknown,
                }

                if self._editing_index is not None:
                    self._events[self._editing_index] = event_data
                else:
                    self._events.append(event_data)

                return await self.async_step_init()

        # Default notify days string
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_EVENT_NAME, default=existing.get(CONF_EVENT_NAME, "")
                ): str,
                vol.Required(
                    CONF_EVENT_DATE,
                    default=existing.get(CONF_EVENT_DATE, ""),
                    description={"suggested_value": "YYYY-MM-DD or MM-DD"},
                ): str,
                vol.Required(
                    CONF_EVENT_TYPE,
                    default=existing.get(CONF_EVENT_TYPE, "birthday"),
                ): vol.In(EVENT_TYPES),
                vol.Optional(
                    CONF_EVENT_CUSTOM_LABEL,
                    default=existing.get(CONF_EVENT_CUSTOM_LABEL, ""),
                ): str,
                vol.Optional(
                    CONF_EVENT_ICON,
                    default=existing.get(CONF_EVENT_ICON, ""),
                ): str,
                vol.Optional(
                    CONF_EVENT_YEAR_UNKNOWN,
                    default=existing.get(CONF_EVENT_YEAR_UNKNOWN, False),
                ): bool,
            }
        )

        # Show delete option if editing
        description_placeholders = {}
        if self._editing_index is not None:
            description_placeholders["edit_mode"] = "true"

        return self.async_show_form(
            step_id="event_form",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )


# ── Helpers ────────────────────────────────────────────────────────────────

def _event_summary(event: dict) -> str:
    """Return a short human-readable summary of an event for the menu."""
    name = event.get(CONF_EVENT_NAME, "Unknown")
    etype = event.get(CONF_EVENT_TYPE, "")
    date_str = event.get(CONF_EVENT_DATE, "")
    return f"{name} — {etype} ({date_str})"


def _validate_date(date_str: str, year_unknown: bool) -> bool:
    """Return True if the date string is valid."""
    from datetime import datetime
    date_str = date_str.strip()
    if year_unknown:
        # Accept MM-DD only
        try:
            datetime.strptime(date_str, "%m-%d")
            return True
        except ValueError:
            pass
    # Accept YYYY-MM-DD
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        pass
    return False
