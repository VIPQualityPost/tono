"""Importer for Nanonis SXM files.

Extension: .sxm
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".sxm"})
calibrated = True

# nanonispy exposes raw header floats for scan_range; the unit lives in
# scan_range_unit, so lateral extents must be converted explicitly.
_UNIT_TO_METERS: dict[str, float] = {
    "m": 1.0,
    "cm": 1e-2,
    "mm": 1e-3,
    "um": 1e-6,
    "µm": 1e-6,
    "nm": 1e-9,
}


def _meters(value: float, unit: object) -> float:
    text = str(unit or "").strip()
    if isinstance(unit, (bytes, bytearray)):
        text = bytes(unit).decode("utf-8", errors="replace").strip().lower()
    else:
        text = text.lower()
    return float(value) * _UNIT_TO_METERS.get(text, 1.0)


def load(path: Path) -> list[DataField]:
    import nanonispy as nap
    sxm = nap.read.Scan(str(path))
    signals = sxm.signals
    if not signals:
        raise ValueError(f"No signals found in {path.name}")

    scan_range = sxm.header.get("scan_range", [1e-6, 1e-6])
    range_units = sxm.header.get("scan_range_unit", ["m", "m"])
    xreal = _meters(scan_range[0], range_units[0] if len(range_units) > 0 else "m")
    yreal = _meters(scan_range[1], range_units[1] if len(range_units) > 1 else "m")

    fields = []
    for sig in signals.values():
        data = sig.get("forward", list(sig.values())[0])
        data = np.asarray(data, dtype=np.float64)
        if data.ndim != 2:
            data = data.reshape(data.shape[-2], data.shape[-1])
        fields.append(DataField(
            data=data,
            xreal=xreal,
            yreal=yreal,
            si_unit_xy="m",
            si_unit_z="m",
        ))
    return fields


def channel_names(path: Path) -> list[str]:
    import nanonispy as nap
    try:
        sxm = nap.read.Scan(str(path))
        if sxm.signals:
            return list(sxm.signals.keys())
    except Exception:
        pass
    return []
