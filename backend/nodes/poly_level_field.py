from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Polynomial Level")
class PolyLevelField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "degree_x": ("INT", {"default": 2, "min": 0, "max": 5, "step": 1}),
                "degree_y": ("INT", {"default": 2, "min": 0, "max": 5, "step": 1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD", "DATA_FIELD")
    RETURN_NAMES = ("leveled", "background")
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit and subtract a polynomial background of given degree in x and y. "
        "Equivalent to gwy_data_field_fit_polynom."
    )

    def process(self, field: DataField, degree_x: int, degree_y: int) -> tuple:
        data = field.data.copy()
        yres, xres = data.shape

        x = np.linspace(0.0, 1.0, xres)
        y = np.linspace(0.0, 1.0, yres)
        xx, yy = np.meshgrid(x, y)

        cols = []
        for i in range(degree_x + 1):
            for j in range(degree_y + 1):
                cols.append((xx ** i * yy ** j).ravel())
        A = np.column_stack(cols)
        z = data.ravel()

        coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)

        background = (A @ coeffs).reshape(yres, xres)
        leveled = data - background

        return (field.replace(data=leveled), field.replace(data=background))
