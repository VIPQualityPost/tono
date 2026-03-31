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
        data = np.array(ch.data, dtype=np.float64).reshape(ch.yres, ch.xres)
        fields.append(DataField(
            data=data,
            xreal=float(ch.xreal),
            yreal=float(ch.yreal),
            xoff=float(getattr(ch, "xoff", 0.0)),
            yoff=float(getattr(ch, "yoff", 0.0)),
            si_unit_xy="m",
            si_unit_z="m",
        ))
    return fields


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
