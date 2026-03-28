from __future__ import annotations

from backend.data_types import DataField


_LENGTH_UNITS = {"m", "km", "cm", "mm", "um", "µm", "nm", "pm", "fm"}


def unit_dimension_key(unit: str) -> str:
    text = str(unit or "").strip().replace("µ", "u")
    if not text:
        return ""
    if text in _LENGTH_UNITS:
        return "length"
    return text


def require_compatible_xy_z_units(field: DataField, node_name: str) -> None:
    xy_key = unit_dimension_key(field.si_unit_xy)
    z_key = unit_dimension_key(field.si_unit_z)
    if xy_key and z_key and xy_key != z_key:
        raise ValueError(f"{node_name} requires compatible XY and Z units, matching Gwyddion's topography-only behavior.")
