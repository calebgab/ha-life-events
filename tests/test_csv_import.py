"""Tests for Life Events CSV import helpers."""

from pathlib import Path

import pytest

from custom_components.life_events.csv_import import (
    merge_events,
    read_import_csv,
    resolve_import_path,
)


def test_resolve_import_path_restricts_files_to_config(tmp_path: Path) -> None:
    """Relative paths stay in config and parent traversal is rejected."""
    assert resolve_import_path(str(tmp_path), "events.csv") == tmp_path / "events.csv"
    assert resolve_import_path(str(tmp_path), "../events.csv") is None


def test_read_import_csv_normalises_values(tmp_path: Path) -> None:
    """CSV rows are stripped, normalised, and assigned event IDs."""
    import_file = tmp_path / "events.csv"
    import_file.write_text(
        "name,date,type,year_unknown,custom_label,icon\n"
        " Sarah ,1990-3-5,BIRTHDAY,false,,\n"
        "Adoption Day,9-4,custom,,Gotcha Day,mdi:paw\n",
        encoding="utf-8",
    )

    events = read_import_csv(import_file)

    assert events[0] | {"_id": "ignored"} == {
        "_id": "ignored",
        "name": "Sarah",
        "date": "1990-03-05",
        "type": "birthday",
        "custom_label": "",
        "icon": "",
        "year_unknown": False,
    }
    assert events[1]["date"] == "09-04"
    assert events[1]["year_unknown"] is True
    assert len(events[0]["_id"]) == 8


@pytest.mark.parametrize(
    "contents",
    [
        "name,date\nSarah,1990-03-05\n",
        "name,date,type\n,1990-03-05,birthday\n",
        "name,date,type\nSarah,1990-03-05,holiday\n",
        "name,date,type\nSarah,2025-02-30,birthday\n",
    ],
)
def test_read_import_csv_rejects_invalid_rows(
    tmp_path: Path, contents: str
) -> None:
    """Invalid headers and row values fail the whole import."""
    import_file = tmp_path / "events.csv"
    import_file.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError):
        read_import_csv(import_file)


def test_merge_events_skips_normalised_duplicates() -> None:
    """Deduplication ignores name punctuation and case."""
    existing = [{"name": "Mum & Dad", "date": "06-12", "type": "anniversary"}]
    duplicate = [{"name": "mum dad", "date": "06-12", "type": "anniversary"}]
    new_event = [{"name": "Sarah", "date": "03-15", "type": "birthday"}]

    assert merge_events(existing, duplicate + new_event) == existing + new_event
