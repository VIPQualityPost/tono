"""Tilt — apply or remove a linear tilt."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Tilt")
class Tilt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "slope_x": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.001}),
                "slope_y": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.001}),
                "mode": (["add", "subtract"], {"default": "add"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'tilted'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply or subtract a linear tilt (plane). slope_x and slope_y are "
        "in data units per physical unit (e.g., m/m for height data). "
        "Use 'subtract' mode to remove a known tilt. "
    )

    KEYWORDS = ("slope", "plane", "level", "bow", "ramp")

    def process(self, field: DataField, slope_x: float, slope_y: float,
                mode: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        x = np.arange(xres) * field.dx
        y = np.arange(yres) * field.dy
        X, Y = np.meshgrid(x, y)

        tilt_plane = slope_x * X + slope_y * Y

        if mode == "subtract":
            return (field.replace(data=data - tilt_plane),)
        else:
            return (field.replace(data=data + tilt_plane),)
