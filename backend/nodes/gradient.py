from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Gradient")
class Gradient:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "component": (["magnitude", "x", "y", "azimuth"],),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'gradient'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the spatial gradient using a Sobel operator. "
        "'x'/'y' give the physical gradient components (z_unit/xy_unit); "
        "'magnitude' gives sqrt(gx²+gy²); "
        "'azimuth' gives the local slope direction in radians via atan2(gy, gx). "
        "Equivalent to gwy_data_field_filter_sobel in Gwyddion (gradient.c)."
    )

    def process(self, field: DataField, component: str) -> tuple:
        from scipy.ndimage import sobel

        data = field.data
        # Sobel kernel sums to ±8 over 2-pixel span; divide by 8·dx to get z/xy slope.
        gx = sobel(data, axis=1) / (8.0 * field.dx)
        gy = sobel(data, axis=0) / (8.0 * field.dy)

        if component == "magnitude":
            result = np.hypot(gx, gy)
            z = str(field.si_unit_z or "").strip()
            xy = str(field.si_unit_xy or "").strip()
            out_unit_z = f"{z}/{xy}" if z and xy else (z or xy)
        elif component == "x":
            result = gx
            z = str(field.si_unit_z or "").strip()
            xy = str(field.si_unit_xy or "").strip()
            out_unit_z = f"{z}/{xy}" if z and xy else (z or xy)
        elif component == "y":
            result = gy
            z = str(field.si_unit_z or "").strip()
            xy = str(field.si_unit_xy or "").strip()
            out_unit_z = f"{z}/{xy}" if z and xy else (z or xy)
        elif component == "azimuth":
            # Azimuth: local slope direction, radians, matches Gwyddion's filter_azimuth
            result = np.arctan2(gy, gx)
            out_unit_z = "rad"
        else:
            raise ValueError(f"Unknown gradient component: {component!r}")

        return (field.replace(data=result, si_unit_z=out_unit_z),)
