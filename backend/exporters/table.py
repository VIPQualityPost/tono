"""
Exporter for RECORD_TABLE and DATA_TABLE values.

Both types are list-of-dict; the Save node currently accepts plain lists in
this slot too, which is preserved here. CSV auto-derives its column set from
the first row's keys (and any additional keys that appear later), matching
the prior behavior.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("RECORD_TABLE", "DATA_TABLE")

FORMATS: dict[str, FormatSpec] = {
    "CSV":  FormatSpec(ext=".csv",  round_trip=True, label="CSV"),
    "JSON": FormatSpec(ext=".json", round_trip=True, label="JSON"),
}


def save(path: Path, value: list, format_name: str, **_opts) -> None:
    rows = list(value)
    if format_name == "JSON":
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return
    if format_name == "CSV":
        columns: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                for key in row.keys():
                    if key not in columns:
                        columns.append(str(key))
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow(row if isinstance(row, dict) else {"value": row})
        return
    raise ValueError(f"Format {format_name!r} is not supported for table inputs.")
