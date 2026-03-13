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
            # Handle delete checkbox
            if user_input.get("delete_event") and self._editing_index is not None:
                self._events.pop(self._editing_index)
                return await self.async_step_init()

            # Normalise and validate date format
            date_str: str = user_input.get(CONF_EVENT_DATE, "")
            year_unknown: bool = user_input.get(CONF_EVENT_YEAR_UNKNOWN, False)
            normalised_date = _normalise_date(date_str, year_unknown)

            if normalised_date is None:
                errors[CONF_EVENT_DATE] = "invalid_date"
            else:
                event_data = {
                    "_id": existing.get("_id") or str(uuid.uuid4())[:8],
                    CONF_EVENT_NAME: user_input[CONF_EVENT_NAME].strip(),
                    CONF_EVENT_DATE: normalised_date,
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

        # Build the existing date's suggested_value: use the stored date when
        # editing so HA's frontend pre-fills the field, fall back to the
        # placeholder hint when adding a new event.
        existing_date = existing.get(CONF_EVENT_DATE, "")
        date_suggested = existing_date if existing_date else "YYYY-MM-DD or MM-DD"

        schema_dict = {
            vol.Required(
                CONF_EVENT_NAME, default=existing.get(CONF_EVENT_NAME, "")
            ): str,
            vol.Required(
                CONF_EVENT_DATE,
                default=existing_date,
                description={"suggested_value": date_suggested},
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

        if self._editing_index is not None:
            schema_dict[vol.Optional("delete_event", default=False)] = bool

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="event_form",
            data_schema=schema,
            errors=errors,
        )


# ── Helpers ────────────────────────────────────────────────────────────────

def _event_summary(event: dict) -> str:
    """Return a short human-readable summary of an event for the menu."""
    name = event.get(CONF_EVENT_NAME, "Unknown")
    etype = event.get(CONF_EVENT_TYPE, "")
    date_str = event.get(CONF_EVENT_DATE, "")
    return f"{name} — {etype} ({date_str})"


def _normalise_date(date_str: str, year_unknown: bool) -> str | None:
    """Parse a loosely-formatted date string and return it in the correct format.

    Accepts YYYY-M-D, YYYY-MM-D, YYYY-M-DD, YYYY-MM-DD (when year_unknown=False)
    and M-D, MM-D, M-DD, MM-DD (when year_unknown=True).
    Returns the normalised string on success, or None if unparseable.
    """
    import re
    date_str = date_str.strip()

    if year_unknown:
        # Match M-D or MM-DD (with or without leading zeros)
        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", date_str)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{month:02d}-{day:02d}"
    else:
        # Match YYYY-M-D variants
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d}"

    return None
