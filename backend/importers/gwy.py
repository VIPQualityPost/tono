from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".gwy"})
calibrated = True


def load(path: Path) -> list[DataField]:
    import gwyfile
    obj = gwyfile.load(str(path))
    channels = gwyfile.util.get_datafields(obj)
    if not channels:
        raise ValueError(f"No data channels found in {path.name}")

    fields = []
    for ch in channels.values():
        # gwyfile.objects.GwyDataField exposes .data as an already-2D ndarray
        # (no xres/yres attributes — those were removed in gwyfile 0.3+).
        data = np.asarray(ch.data, dtype=np.float64)
        if data.ndim != 2:
            # Defensive: if a future gwyfile version yields a flat buffer, the
            # dimensions live in the serialized object's xres/yres keys.
            xres = int(ch.get("xres", data.size))
            yres = int(ch.get("yres", 1))
            data = data.reshape(yres, xres)
        fields.append(DataField(
            data=data,
            xreal=float(ch.xreal),
            yreal=float(ch.yreal),
            xoff=float(getattr(ch, "xoff", 0.0)),
            yoff=float(getattr(ch, "yoff", 0.0)),
            si_unit_xy=_unit_str(getattr(ch, "si_unit_xy", None)) or "m",
            si_unit_z=_unit_str(getattr(ch, "si_unit_z", None)) or "m",
        ))
    return fields


def _unit_str(si_unit: object) -> str:
    """Extract the unit string from a GwySIUnit without importing gwyfile.

    Loaded GwySIUnit objects behave like dicts with a ``unitstr`` key.
    """
    if si_unit is None:
        return ""
    if hasattr(si_unit, "unitstr"):
        return str(getattr(si_unit, "unitstr") or "")
    try:
        return str(si_unit["unitstr"] or "")
    except (KeyError, TypeError):
        return ""


def channel_names(path: Path) -> list[str]:
    import gwyfile
    try:
        obj = gwyfile.load(str(path))
        channels = gwyfile.util.get_datafields(obj)
        if channels:
            return list(channels.keys())
    except Exception:
        pass
    return []
