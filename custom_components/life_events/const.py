"""Constants for the Life Events integration."""

DOMAIN = "life_events"
COORDINATOR = "coordinator"

# Event types
EVENT_TYPE_BIRTHDAY = "birthday"
EVENT_TYPE_ANNIVERSARY = "anniversary"
EVENT_TYPE_CUSTOM = "custom"

EVENT_TYPES = [EVENT_TYPE_BIRTHDAY, EVENT_TYPE_ANNIVERSARY, EVENT_TYPE_CUSTOM]

EVENT_TYPE_ICONS = {
    EVENT_TYPE_BIRTHDAY: "mdi:cake-variant",
    EVENT_TYPE_ANNIVERSARY: "mdi:ring",
    EVENT_TYPE_CUSTOM: "mdi:calendar-star",
}

EVENT_TYPE_LABELS = {
    EVENT_TYPE_BIRTHDAY: "Birthday",
    EVENT_TYPE_ANNIVERSARY: "Anniversary",
    EVENT_TYPE_CUSTOM: "Custom",
}

# Config / options keys
CONF_EVENTS = "events"
CONF_EVENT_NAME = "name"
CONF_EVENT_DATE = "date"
CONF_EVENT_TYPE = "type"
CONF_EVENT_CUSTOM_LABEL = "custom_label"
CONF_EVENT_ICON = "icon"
CONF_EVENT_YEAR_UNKNOWN = "year_unknown"

# Sensor attributes
ATTR_NEXT_DATE = "next_date"
ATTR_DAYS_UNTIL = "days_until"
ATTR_AGE_AT_NEXT = "age_at_next"
ATTR_YEARS_AT_NEXT = "years_at_next"
ATTR_EVENT_TYPE = "event_type"
ATTR_EVENT_LABEL = "event_label"
ATTR_YEAR_UNKNOWN = "year_unknown"
ATTR_ORIGINAL_DATE = "original_date"

# Calendar
CALENDAR_NAME = "Life Events"

# Update interval: recalculate hourly
UPDATE_INTERVAL_HOURS = 1
