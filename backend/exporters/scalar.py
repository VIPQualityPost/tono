"""
Exporter for FLOAT scalars (also handles Python int and numpy scalar types).
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("FLOAT",)

FORMATS: dict[str, FormatSpec] = {
    "TXT":  FormatSpec(ext=".txt",  round_trip=True, label="Text"),
    "JSON": FormatSpec(ext=".json", round_trip=True, label="JSON"),
}


def save(path: Path, value: float, format_name: str, **_opts) -> None:
    numeric = float(value)
    if format_name == "TXT":
        path.write_text(f"{numeric}\n", encoding="utf-8")
        return
    if format_name == "JSON":
        path.write_text(json.dumps({"value": numeric}, indent=2), encoding="utf-8")
        return
    raise ValueError(f"Format {format_name!r} is not supported for scalar values.")
