from __future__ import annotations

import numpy as np

from backend.data_types import DataField


_LENGTH_UNITS = {"m", "km", "cm", "mm", "um", "µm", "nm", "pm", "fm"}


def unit_dimension_key(unit: str) -> str:
    text = str(unit or "").strip().replace("µ", "u")
    if not text:
        return ""
    if text in _LENGTH_UNITS:
        return "length"
    return text


def slope_unit(field: DataField) -> str:
    """Return the physical slope unit string (z_unit/xy_unit)."""
    z = str(field.si_unit_z or "").strip()
    xy = str(field.si_unit_xy or "").strip()
    return f"{z}/{xy}" if z and xy else (z or xy)


def physical_sobel_gradient(field: DataField) -> tuple[np.ndarray, np.ndarray]:
    """Compute physical Sobel gradient (gx, gy) in z_unit/xy_unit."""
    from scipy.ndimage import sobel
    gx = sobel(field.data, axis=1) / (8.0 * field.dx)
    gy = sobel(field.data, axis=0) / (8.0 * field.dy)
    return gx, gy


def require_compatible_xy_z_units(field: DataField, node_name: str) -> None:
    xy_key = unit_dimension_key(field.si_unit_xy)
    z_key = unit_dimension_key(field.si_unit_z)
    if xy_key and z_key and xy_key != z_key:
        raise ValueError(f"{node_name} requires compatible XY and Z units, matching Gwyddion's topography-only behavior.")
