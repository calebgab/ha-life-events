"""CSV import helpers for Life Events."""

from __future__ import annotations

import csv
import re
import uuid
from datetime import date
from pathlib import Path

from .const import (
    CONF_EVENT_CUSTOM_LABEL,
    CONF_EVENT_DATE,
    CONF_EVENT_ICON,
    CONF_EVENT_NAME,
    CONF_EVENT_TYPE,
    CONF_EVENT_YEAR_UNKNOWN,
    EVENT_TYPES,
)

MAX_IMPORT_BYTES = 1_000_000


def resolve_import_path(config_dir: str, value: str) -> Path | None:
    """Resolve an import path and restrict it to the HA config directory."""
    root = Path(config_dir).resolve()
    candidate = Path(value.strip())
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _normalise_date(date_str: str, year_unknown: bool) -> str | None:
    """Return a validated date in YYYY-MM-DD or MM-DD format."""
    date_str = date_str.strip()
    pattern = (
        r"(\d{1,2})-(\d{1,2})"
        if year_unknown
        else r"(\d{4})-(\d{1,2})-(\d{1,2})"
    )
    match = re.fullmatch(pattern, date_str)
    if match is None:
        return None

    values = [int(value) for value in match.groups()]
    try:
        if year_unknown:
            month, day = values
            date(2000, month, day)
            return f"{month:02d}-{day:02d}"
        year, month, day = values
        date(year, month, day)
        return f"{year}-{month:02d}-{day:02d}"
    except ValueError:
        return None


def read_import_csv(path: Path) -> list[dict]:
    """Read and validate an import CSV without changing integration state."""
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("CSV exceeds the 1 MB import limit")

    events: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {CONF_EVENT_NAME, CONF_EVENT_DATE, CONF_EVENT_TYPE}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain name, date, and type columns")

        for line_number, row in enumerate(reader, start=2):
            name = (row.get(CONF_EVENT_NAME) or "").strip()
            event_type = (row.get(CONF_EVENT_TYPE) or "").strip().lower()
            raw_date = (row.get(CONF_EVENT_DATE) or "").strip()
            raw_year_unknown = (
                row.get(CONF_EVENT_YEAR_UNKNOWN) or ""
            ).strip().lower()
            year_unknown = raw_year_unknown in {"1", "true", "yes", "on"}
            if len(raw_date) <= 5:
                year_unknown = True
            normalised_date = _normalise_date(raw_date, year_unknown)

            if not name:
                raise ValueError(f"line {line_number}: name is required")
            if event_type not in EVENT_TYPES:
                raise ValueError(f"line {line_number}: invalid event type")
            if normalised_date is None:
                raise ValueError(f"line {line_number}: invalid date")

            events.append(
                {
                    "_id": str(uuid.uuid4())[:8],
                    CONF_EVENT_NAME: name,
                    CONF_EVENT_DATE: normalised_date,
                    CONF_EVENT_TYPE: event_type,
                    CONF_EVENT_CUSTOM_LABEL: (
                        row.get(CONF_EVENT_CUSTOM_LABEL) or ""
                    ).strip(),
                    CONF_EVENT_ICON: (row.get(CONF_EVENT_ICON) or "").strip(),
                    CONF_EVENT_YEAR_UNKNOWN: year_unknown,
                }
            )

    if not events:
        raise ValueError("CSV contains no events")
    return events


def _event_key(event: dict) -> tuple[str, str, str]:
    """Return the stable identity used for import deduplication."""
    name = re.sub(r"[^\w]", "", event.get(CONF_EVENT_NAME, "").casefold())
    return (
        name,
        event.get(CONF_EVENT_DATE, ""),
        event.get(CONF_EVENT_TYPE, ""),
    )


def merge_events(existing: list[dict], imported: list[dict]) -> list[dict]:
    """Merge imported records while preserving existing duplicates."""
    merged = list(existing)
    keys = {_event_key(event) for event in merged}
    for event in imported:
        key = _event_key(event)
        if key not in keys:
            merged.append(event)
            keys.add(key)
    return merged
