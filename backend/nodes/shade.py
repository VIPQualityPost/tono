"""Shaded presentation — render surface with directional lighting."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import sobel

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Shade")
class Shade:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "azimuth": ("FLOAT", {"default": 315.0, "min": 0.0, "max": 360.0, "step": 1.0}),
                "elevation": ("FLOAT", {"default": 45.0, "min": 5.0, "max": 85.0, "step": 1.0}),
                "blend": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'shaded'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Render a surface with directional hillshade lighting. "
        "Azimuth controls the light direction (0=north, 90=east). "
        "Elevation controls the light angle above the horizon. "
        "Blend mixes original data (0) with shaded relief (1). "
    )

    def process(self, field: DataField, azimuth: float, elevation: float,
                blend: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        gx = sobel(data, axis=1) / (8.0 * field.dx)
        gy = sobel(data, axis=0) / (8.0 * field.dy)

        az_rad = np.radians(azimuth)
        el_rad = np.radians(elevation)

        # Lambertian shading
        lx = np.cos(el_rad) * np.sin(az_rad)
        ly = np.cos(el_rad) * np.cos(az_rad)
        lz = np.sin(el_rad)

        normal_z = 1.0 / np.sqrt(gx**2 + gy**2 + 1.0)
        normal_x = -gx * normal_z
        normal_y = -gy * normal_z

        shade = np.clip(normal_x * lx + normal_y * ly + normal_z * lz, 0.0, 1.0)

        # Normalize original data to [0, 1]
        dmin, dmax = data.min(), data.max()
        if dmax > dmin:
            norm_data = (data - dmin) / (dmax - dmin)
        else:
            norm_data = np.ones_like(data) * 0.5

        result = (1.0 - blend) * norm_data + blend * shade
        return (field.replace(data=result, si_unit_z=""),)
