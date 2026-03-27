from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Plane Level")
class PlaneLevelField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("leveled",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit and subtract a least-squares plane from the data. "
        "Equivalent to gwy_data_field_fit_plane + gwy_data_field_plane_level."
    )

    def process(self, field: DataField) -> tuple:
        data = field.data.copy()
        yres, xres = data.shape

        x = np.linspace(0.0, 1.0, xres)
        y = np.linspace(0.0, 1.0, yres)
        xx, yy = np.meshgrid(x, y)

        A = np.column_stack([
            np.ones(xres * yres),
            xx.ravel(),
            yy.ravel(),
        ])
        z = data.ravel()

        coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
        pa, pbx, pby = coeffs

        plane = (pa + pbx * xx + pby * yy)
        return (field.replace(data=data - plane),)
