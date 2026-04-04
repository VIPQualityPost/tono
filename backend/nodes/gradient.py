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
        from backend.nodes.surface_common import physical_sobel_gradient, slope_unit

        gx, gy = physical_sobel_gradient(field)

        if component == "magnitude":
            result = np.hypot(gx, gy)
            out_unit_z = slope_unit(field)
        elif component == "x":
            result = gx
            out_unit_z = slope_unit(field)
        elif component == "y":
            result = gy
            out_unit_z = slope_unit(field)
        elif component == "azimuth":
            result = np.arctan2(gy, gx)
            out_unit_z = "rad"
        else:
            raise ValueError(f"Unknown gradient component: {component!r}")

        return (field.replace(data=result, si_unit_z=out_unit_z),)
