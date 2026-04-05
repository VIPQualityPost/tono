"""
Exporter registry.

Each module in this package exports a tuple of tono type names it can handle
(`accepted_types`), a FORMATS map of format name → FormatSpec, and a `save()`
function. This registry walks those modules and builds lookup tables the
Save node uses to dispatch.

Usage::

    from backend.exporters import get_exporter, resolve_path, type_name_for_value

    type_name = type_name_for_value(value)          # e.g. "DATA_FIELD"
    exporter, spec = get_exporter(type_name, "GWY") # raises on unknown combo
    path = resolve_path(filename, spec)
    exporter.save(path, value, "GWY")
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from backend.data_types import (
    DataField,
    DataTable,
    ImageData,
    LineData,
    MeshModel,
    RecordTable,
)
from backend.exporters import datafield, image, line, mesh, scalar, table
from backend.exporters._base import Exporter, FormatSpec

_EXPORTER_MODULES: list[ModuleType] = [datafield, image, line, mesh, scalar, table]

# (type_name, format_name) → (module, FormatSpec)
_REGISTRY: dict[tuple[str, str], tuple[ModuleType, FormatSpec]] = {}
for _mod in _EXPORTER_MODULES:
    for _type_name in _mod.accepted_types:
        for _format_name, _spec in _mod.FORMATS.items():
            _REGISTRY[(_type_name, _format_name)] = (_mod, _spec)


def get_exporter(type_name: str, format_name: str) -> tuple[ModuleType, FormatSpec]:
    """Return the (module, FormatSpec) for a type + format combination.

    Raises ValueError with a user-readable message when the combination is
    unknown. That message gets propagated straight to the UI status toast,
    so keep it actionable.
    """
    entry = _REGISTRY.get((type_name, format_name))
    if entry is None:
        raise ValueError(f"Format {format_name!r} is not supported for {type_name}.")
    return entry


def available_formats(type_name: str) -> list[str]:
    """Format names available for a given tono type, in registration order."""
    return [fmt for (t, fmt) in _REGISTRY if t == type_name]


def type_name_for_value(value: Any) -> str:
    """Classify a runtime Python value into a tono type name.

    The ordering matters: ImageData is a subclass of ndarray, and RecordTable /
    DataTable are subclasses of list, so check the more specific classes first.
    """
    if isinstance(value, MeshModel):
        return "MESH_MODEL"
    if isinstance(value, DataField):
        return "DATA_FIELD"
    if isinstance(value, LineData):
        return "LINE"
    if isinstance(value, ImageData):
        # Annotation outputs carry context in ``.metadata``; regardless, image
        # formats are the right set.
        return "IMAGE"
    if isinstance(value, np.ndarray):
        if value.ndim == 1:
            return "LINE"
        return "IMAGE"
    if isinstance(value, RecordTable):
        return "RECORD_TABLE"
    if isinstance(value, DataTable):
        return "DATA_TABLE"
    if isinstance(value, list):
        # Plain list — treat as a data table; the table exporter handles both.
        return "DATA_TABLE"
    if isinstance(value, (int, float, np.floating, np.integer)):
        return "FLOAT"
    raise ValueError(f"Save does not support input type: {type(value).__name__}")


def resolve_path(filename: str, spec: FormatSpec, default_dir: Path) -> Path:
    """Expand *filename* into an absolute Path with the correct extension.

    Relative names are written under *default_dir* (the session download dir);
    absolute paths are honored as-is, with parent directories created.
    """
    raw_filename = str(filename).strip() if filename is not None else ""
    if not raw_filename:
        raise ValueError("No output filename selected — enter a file name.")

    candidate = Path(raw_filename).expanduser()
    if candidate.is_absolute():
        candidate.parent.mkdir(parents=True, exist_ok=True)
        path = candidate
    else:
        default_dir.mkdir(parents=True, exist_ok=True)
        path = default_dir / candidate.name

    if path.suffix.lower() != spec.ext:
        path = path.with_suffix(spec.ext)
    return path


__all__ = [
    "Exporter",
    "FormatSpec",
    "available_formats",
    "get_exporter",
    "resolve_path",
    "type_name_for_value",
]
