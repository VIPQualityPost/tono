"""
Importer for Asylum Research / Ergo HDF5 files (.h5, .hdf5, .he5).

Asylum Research instruments store scan metadata in a sidecar group rather
than as dataset attributes.  This importer reads physical dimensions from:

  Image/DataSetInfo/Global/Channels/<channel>/ImageDims
    DimScaling   – (2,2) array: [[px_size_x, offset_x], [px_size_y, offset_y]]
    DimExtents   – pixel counts [xres, yres] (stored in a child group)
    DimUnits     – lateral unit strings
    DataUnits    – Z unit string

If the sidecar group is absent (generic HDF5), standard dataset attributes
are used as a fallback:

  xreal / yreal   – physical scan size in metres  (fallback: 1e-6)
  xoff  / yoff    – position offset in metres      (fallback: 0)
  si_unit_xy      – lateral unit string            (fallback: "m")
  si_unit_z       – value unit string              (fallback: "m")

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


def _ar_image_dims(f, ds_name: str) -> dict | None:
    """
    Look up Asylum Research ImageDims metadata for a dataset.

    AR .h5 files store scan dimensions in a sibling group rather than as
    dataset attributes.  Given a dataset path like:
      "Image/DataSet/Resolution 0/Frame 0/Adhesion:Retrace/Image"
    the channel name is the second-to-last component ("Adhesion:Retrace"),
    and the metadata lives at:
      "Image/DataSetInfo/Global/Channels/<channel>/ImageDims"

    Returns a dict with xreal, yreal, xoff, yoff, si_unit_xy, si_unit_z,
    or None if the group isn't found.
    """
    import h5py

    parts = ds_name.split("/")
    if len(parts) < 2:
        return None
    channel = parts[-2]

    dims_path = f"Image/DataSetInfo/Global/Channels/{channel}/ImageDims"
    grp = f.get(dims_path)
    if not isinstance(grp, h5py.Group):
        return None

    scaling = grp.attrs.get("DimScaling")   # shape (2, 2): [[px_x, off_x], [px_y, off_y]]
    dim_units = grp.attrs.get("DimUnits")   # array of unit strings, e.g. ['m', 'm']
    data_units = grp.attrs.get("DataUnits") # Z unit string, e.g. 'N'

    if scaling is None or np.asarray(scaling).shape != (2, 2):
        return None

    scaling = np.asarray(scaling, dtype=np.float64)
    px_x, off_x = float(scaling[0, 0]), float(scaling[0, 1])
    px_y, off_y = float(scaling[1, 0]), float(scaling[1, 1])

    # DimExtents gives pixel counts; use to compute total physical size.
    extents_grp = None
    for child_name in grp:
        child = grp[child_name]
        if isinstance(child, h5py.Group) and "DimExtents" in child.attrs:
            extents_grp = child
            break

    xres, yres = 1, 1
    if extents_grp is not None:
        ext = np.asarray(extents_grp.attrs["DimExtents"])
        if ext.size >= 2:
            xres, yres = int(ext[0]), int(ext[1])

    def _decode(raw, default="m") -> str:
        if raw is None:
            return default
        if hasattr(raw, "__iter__") and not isinstance(raw, (str, bytes)):
            raw = list(raw)[0] if len(raw) else default
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace").strip() or default
        return str(raw).strip() or default

    return {
        "xreal": abs(px_x * xres) or 1e-6,
        "yreal": abs(px_y * yres) or 1e-6,
        "xoff":  off_x,
        "yoff":  off_y,
        "si_unit_xy": _decode(dim_units[0] if dim_units is not None and len(dim_units) >= 1 else None),
        "si_unit_z":  _decode(data_units),
    }


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

            # Try Asylum Research sidecar metadata first, then dataset attrs.
            ar = _ar_image_dims(f, name)
            if ar:
                fields.append(DataField(
                    data=data,
                    xreal=ar["xreal"], yreal=ar["yreal"],
                    xoff=ar["xoff"],   yoff=ar["yoff"],
                    si_unit_xy=ar["si_unit_xy"],
                    si_unit_z=ar["si_unit_z"],
                ))
            else:
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


def _display_names(full_names: list[str]) -> list[str]:
    """
    Derive short display names from HDF5 dataset paths.

    Rules (all comparisons case-insensitive):
      1. All thumbnail datasets are filtered out.
      2. Display name = second-to-last path component (drops the leaf like
         "/image" or "/thumbnail").
      3. "global" channels sort to the front.
      4. If two kept datasets share the same second-to-last name, the leaf is
         appended to disambiguate.

    Returns a list in sorted order (not parallel to full_names).
    """
    from collections import Counter

    # Filter out all thumbnail datasets.
    kept: list[tuple[int, str]] = []   # (original index, full name)
    for i, name in enumerate(full_names):
        if name.split("/")[-1].lower() == "thumbnail":
            continue
        kept.append((i, name))

    # Sort: "global" second-to-last first, then alphabetical.
    def _sort_key(item: tuple[int, str]) -> tuple[int, str]:
        parts = item[1].split("/")
        second_last = parts[-2].lower() if len(parts) >= 2 else parts[-1].lower()
        return (0 if second_last == "global" else 1, second_last)

    kept.sort(key=_sort_key)

    # Build short names (second-to-last), disambiguate clashes.
    short = [
        (parts[-2] if len(parts := name.split("/")) >= 2 else parts[-1])
        for _, name in kept
    ]
    counts = Counter(short)
    disambiguated = [
        f"{s}/{name.split('/')[-1]}" if counts[s] > 1 else s
        for s, (_, name) in zip(short, kept)
    ]

    return disambiguated


def channel_names(path: Path) -> list[str]:
    try:
        import h5py
    except ImportError:
        return []
    try:
        with h5py.File(str(path), "r") as f:
            datasets = _iter_2d_datasets(f)
            full_names = [name for name, _ in datasets]
        return [n for n in _display_names(full_names) if n is not None]
    except Exception:
        return []
