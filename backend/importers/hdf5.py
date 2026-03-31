"""
Generic HDF5 importer (.h5, .hdf5, .he5).

Each 2-D dataset found in the file is returned as a DataField.  Physical
dimensions are read from standard dataset attributes if present:

  xreal / yreal   – physical scan size in metres  (fallback: 1e-6)
  xoff  / yoff    – position offset in metres      (fallback: 0)
  si_unit_xy      – lateral unit string            (fallback: "m")
  si_unit_z       – value unit string              (fallback: "m")

For Asylum Research / Ergo format files (which store scan metadata in a
sidecar group rather than as dataset attributes), use the ergo_hdf5 importer.

Requires:
    pip install h5py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".h5", ".hdf5", ".he5"})
calibrated = True   # we attempt to read physical metadata


def _iter_2d_datasets(h5file):
    """Yield (name, dataset) for every 2-D numeric dataset in the file."""
    import h5py

    def _visit(name, obj):
        if isinstance(obj, h5py.Dataset) and obj.ndim == 2 and np.issubdtype(obj.dtype, np.number):
            results.append((name, obj))

    results: list = []
    h5file.visititems(_visit)
    return results


def _attr_str(attrs, key: str, default: str) -> str:
    val = attrs.get(key)
    if val is None:
        return default
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace").strip() or default
    return str(val).strip() or default


def _attr_float(attrs, key: str, default: float) -> float:
    val = attrs.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def load(path: Path) -> list[DataField]:
    try:
        import h5py
    except ImportError:
        raise ImportError("Install 'h5py' to load HDF5 files:  pip install h5py")

    with h5py.File(str(path), "r") as f:
        datasets = _iter_2d_datasets(f)
        if not datasets:
            raise ValueError(f"No 2-D numeric datasets found in {path.name}")

        fields = []
        for name, ds in datasets:
            data = np.asarray(ds, dtype=np.float64)
            attrs = ds.attrs
            fields.append(DataField(
                data=data,
                xreal=_attr_float(attrs, "xreal", 1e-6),
                yreal=_attr_float(attrs, "yreal", 1e-6),
                xoff=_attr_float(attrs, "xoff", 0.0),
                yoff=_attr_float(attrs, "yoff", 0.0),
                si_unit_xy=_attr_str(attrs, "si_unit_xy", "m"),
                si_unit_z=_attr_str(attrs, "si_unit_z", "m"),
            ))
    return fields


def channel_names(path: Path) -> list[str]:
    try:
        import h5py
    except ImportError:
        return []
    try:
        with h5py.File(str(path), "r") as f:
            datasets = _iter_2d_datasets(f)
            # Return second-to-last component as display name, or full name for
            # top-level datasets.
            names = []
            for full_name, _ in datasets:
                parts = full_name.split("/")
                names.append(parts[-2] if len(parts) >= 2 else parts[-1])
        return names
    except Exception:
        return []
