"""DataUpdateCoordinator for Life Events."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_EVENTS,
    CONF_EVENT_NAME,
    CONF_EVENT_DATE,
    CONF_EVENT_TYPE,
    CONF_EVENT_CUSTOM_LABEL,
    CONF_EVENT_ICON,
    CONF_EVENT_YEAR_UNKNOWN,
    CONF_NOTIFY_DAYS_BEFORE,
    EVENT_TYPE_ICONS,
    EVENT_TYPE_LABELS,
    HA_EVENT_LIFE_EVENT_TODAY,
    HA_EVENT_LIFE_EVENT_UPCOMING,
    DEFAULT_NOTIFY_DAYS,
)

_LOGGER = logging.getLogger(__name__)


def _parse_date(date_str: str) -> date | None:
    """Parse a date string in YYYY-MM-DD or MM-DD format."""
    if not date_str:
        return None
    try:
        if len(date_str) == 10:  # YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        if len(date_str) == 5:  # MM-DD
            # Use a placeholder year; year_unknown should be True in this case
            return datetime.strptime(f"2000-{date_str}", "%Y-%m-%d").date()
    except ValueError:
        _LOGGER.warning("Could not parse date: %s", date_str)
    return None


def _next_occurrence(event_date: date, today: date) -> date:
    """Return the next occurrence of a month/day from today."""
    candidate = event_date.replace(year=today.year)
    if candidate < today:
        candidate = event_date.replace(year=today.year + 1)
    return candidate


def _days_until(next_date: date, today: date) -> int:
    """Return number of days between today and next_date."""
    return (next_date - today).days


def _years_at_next(event_date: date, next_occurrence: date, year_unknown: bool) -> int | None:
    """Return the number of years (age/anniversary number) at next occurrence."""
    if year_unknown:
        return None
    return next_occurrence.year - event_date.year


class LifeEventsCoordinator(DataUpdateCoordinator):
    """Manage fetching and calculating life event data."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),  # Check hourly; recalc is cheap
        )
        self.config_entry = config_entry
        self._fired_today: set[str] = set()
        self._fired_upcoming: dict[str, set[int]] = {}

    @property
    def events_config(self) -> list[dict]:
        """Return the raw events list from options (falling back to data)."""
        return self.config_entry.options.get(
            CONF_EVENTS,
            self.config_entry.data.get(CONF_EVENTS, []),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Calculate all event data. Called by the coordinator on schedule."""
        today = date.today()
        results: dict[str, Any] = {}

        for event in self.events_config:
            name: str = event.get(CONF_EVENT_NAME, "")
            date_str: str = event.get(CONF_EVENT_DATE, "")
            event_type: str = event.get(CONF_EVENT_TYPE, "birthday")
            custom_label: str = event.get(CONF_EVENT_CUSTOM_LABEL, "")
            icon: str = event.get(CONF_EVENT_ICON, "") or EVENT_TYPE_ICONS.get(event_type, "mdi:calendar-star")
            year_unknown: bool = event.get(CONF_EVENT_YEAR_UNKNOWN, False)
            notify_days: list[int] = event.get(CONF_NOTIFY_DAYS_BEFORE, DEFAULT_NOTIFY_DAYS)

            if not name or not date_str:
                continue

            parsed = _parse_date(date_str)
            if parsed is None:
                continue

            next_date = _next_occurrence(parsed, today)
            days = _days_until(next_date, today)
            years = _years_at_next(parsed, next_date, year_unknown)

            label = custom_label if (event_type == "custom" and custom_label) else EVENT_TYPE_LABELS.get(event_type, "Event")

            entity_key = _make_entity_key(name)

            results[entity_key] = {
                CONF_EVENT_NAME: name,
                "next_date": next_date,
                "days_until": days,
                "years_at_next": years,
                "event_type": event_type,
                "event_label": label,
                "icon": icon,
                "year_unknown": year_unknown,
                "original_date": date_str,
            }

            # Fire HA events for automations / blueprints
            self._maybe_fire_events(name, entity_key, days, years, label, notify_days, today)

        # Reset fired tracking at midnight (new day)
        if not hasattr(self, "_last_reset_day") or self._last_reset_day != today:
            self._fired_today = set()
            self._fired_upcoming = {}
            self._last_reset_day = today

        return results

    def _maybe_fire_events(
        self,
        name: str,
        key: str,
        days: int,
        years: int | None,
        label: str,
        notify_days: list[int],
        today: date,
    ) -> None:
        """Fire HA events for today and upcoming notifications."""
        event_data_base = {
            "name": name,
            "event_label": label,
            "years": years,
            "days_until": days,
        }

        if days == 0 and key not in self._fired_today:
            self.hass.bus.async_fire(HA_EVENT_LIFE_EVENT_TODAY, event_data_base)
            self._fired_today.add(key)
            _LOGGER.debug("Fired life_events_today for %s", name)

        for notify_day in notify_days:
            if notify_day == 0:
                continue  # Already handled above
            if days == notify_day:
                fired_set = self._fired_upcoming.setdefault(key, set())
                if notify_day not in fired_set:
                    self.hass.bus.async_fire(
                        HA_EVENT_LIFE_EVENT_UPCOMING,
                        {**event_data_base, "notify_days_before": notify_day},
                    )
                    fired_set.add(notify_day)
                    _LOGGER.debug("Fired life_events_upcoming for %s (%d days)", name, notify_day)

    def get_calendar_events(self, start_date: date, end_date: date) -> list[dict]:
        """Return calendar events within the given date range."""
        if not self.data:
            return []

        calendar_events = []
        
        for event in self.events_config:
            name: str = event.get(CONF_EVENT_NAME, "")
            date_str: str = event.get(CONF_EVENT_DATE, "")
            event_type: str = event.get(CONF_EVENT_TYPE, "birthday")
            custom_label: str = event.get(CONF_EVENT_CUSTOM_LABEL, "")
            year_unknown: bool = event.get(CONF_EVENT_YEAR_UNKNOWN, False)

            if not name or not date_str:
                continue

            parsed = _parse_date(date_str)
            if parsed is None:
                continue

            label = custom_label if (event_type == "custom" and custom_label) else EVENT_TYPE_LABELS.get(event_type, "Event")

            # Generate occurrences within the range
            check_year = start_date.year - 1
            while check_year <= end_date.year + 1:
                try:
                    occurrence = parsed.replace(year=check_year)
                except ValueError:
                    check_year += 1
                    continue

                if start_date <= occurrence <= end_date:
                    years = (occurrence.year - parsed.year) if not year_unknown else None
                    years_str = f" ({years})" if years is not None else ""
                    summary = f"{name}'s {label}{years_str}"

                    calendar_events.append({
                        "uid": f"life_events_{name}_{occurrence.isoformat()}",
                        "summary": summary,
                        "start": occurrence,
                        "end": occurrence + timedelta(days=1),
                        "all_day": True,
                        "description": f"{name}'s {label}" + (f" — turning {years}" if years else ""),
                    })

                check_year += 1

        return sorted(calendar_events, key=lambda e: e["start"])


def _make_entity_key(name: str) -> str:
    """Convert a name to a safe entity key."""
    return name.lower().replace(" ", "_").replace("-", "_")
