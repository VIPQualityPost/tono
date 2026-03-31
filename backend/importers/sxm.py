from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".sxm"})
calibrated = True


def load(path: Path) -> list[DataField]:
    import nanonispy as nap
    sxm = nap.read.Scan(str(path))
    signals = sxm.signals
    if not signals:
        raise ValueError(f"No signals found in {path.name}")

    scan_range = sxm.header.get("scan_range", [1e-6, 1e-6])

    fields = []
    for sig in signals.values():
        data = sig.get("forward", list(sig.values())[0])
        data = np.asarray(data, dtype=np.float64)
        if data.ndim != 2:
            data = data.reshape(data.shape[-2], data.shape[-1])
        fields.append(DataField(
            data=data,
            xreal=float(scan_range[0]),
            yreal=float(scan_range[1]),
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
