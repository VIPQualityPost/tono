from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".ibw"})
calibrated = True


def _load_ibw_raw(path: Path):
    import numpy as _np
    if not hasattr(_np, "complex"):
        setattr(_np, "complex", complex)
    try:
        from igor.binarywave import load as load_ibw
    except ImportError:
        raise ImportError("Install 'igor' to load .ibw files:  pip install igor")
    return load_ibw(str(path))


def _decode_unit(raw_unit) -> str:
    if raw_unit is None:
        return "m"
    if isinstance(raw_unit, bytes):
        return raw_unit.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
    if isinstance(raw_unit, np.ndarray):
        return bytes(raw_unit).split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
    return str(raw_unit).strip() or "m"


def load(path: Path) -> list[DataField]:
    wave = _load_ibw_raw(path)
    wdata = wave["wave"]
    header = wdata["wave_header"]
    raw = wdata["wData"]

    n_channels = raw.shape[2] if raw.ndim >= 3 else 1
    sfA = header.get("sfA", None)

    dim_units_raw = header.get("dimUnits", None)
    data_units_raw = header.get("dataUnits", None)

    if isinstance(dim_units_raw, np.ndarray) and dim_units_raw.ndim == 2:
        si_unit_xy = _decode_unit(dim_units_raw[0])
    elif isinstance(dim_units_raw, (list, np.ndarray)) and len(dim_units_raw) > 0:
        si_unit_xy = _decode_unit(dim_units_raw[0])
    else:
        si_unit_xy = _decode_unit(dim_units_raw)

    si_unit_z = _decode_unit(data_units_raw)

    fields = []
    for ch_idx in range(n_channels):
        if raw.ndim >= 3:
            ch_data = raw[:, :, ch_idx]
        elif raw.ndim == 1:
            ch_data = raw.reshape(-1, 1)
        else:
            ch_data = raw

        data = np.flipud(ch_data.T).astype(np.float64)
        yres, xres = data.shape

        if sfA is not None and len(sfA) >= 2:
            xreal = abs(float(sfA[0]) * xres) or 1e-6
            yreal = abs(float(sfA[1]) * yres) or 1e-6
        else:
            hsA = header.get("hsA", 0.0)
            xreal = abs(float(hsA) * xres) or 1e-6
            yreal = xreal * (yres / xres) if xres else 1e-6

        fields.append(DataField(
            data=data, xreal=xreal, yreal=yreal,
            si_unit_xy=si_unit_xy, si_unit_z=si_unit_z,
        ))
    return fields


def channel_names(path: Path) -> list[str]:
    try:
        wave = _load_ibw_raw(path)
        wdata = wave["wave"]
        raw = wdata["wData"]
        labels = wdata.get("labels", None)

        if raw.ndim >= 3 and labels:
            dim_idx = min(2, len(labels) - 1)
            if dim_idx >= 0 and labels[dim_idx]:
                decoded = []
                for lbl in labels[dim_idx]:
                    if lbl:
                        name = lbl.split(b"\x00")[0].decode("ascii", errors="replace").strip()
                        if name:
                            decoded.append(name)
                if decoded:
                    return decoded

        if raw.ndim >= 3 and raw.shape[2] > 1:
            return [f"ch{i}" for i in range(raw.shape[2])]
    except Exception:
        pass
    return []
