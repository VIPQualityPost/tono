"""
Leveling nodes — background removal and zero correction.

Gwyddion equivalents:
  PlaneLevelField → gwy_data_field_fit_plane + gwy_data_field_plane_level
  PolyLevelField  → gwy_data_field_fit_polynom (via level.c polylevel module)
  FixZero         → fix_zero in level.c

Plane-fit algorithm follows Gwyddion's level.h definition:
  z_fit = pa + pbx * x + pby * y   (least-squares over all pixels)
"""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


# ---------------------------------------------------------------------------
# PlaneLevelField
# ---------------------------------------------------------------------------

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
    CATEGORY = "level"
    DESCRIPTION = (
        "Fit and subtract a least-squares plane from the data. "
        "Equivalent to gwy_data_field_fit_plane + gwy_data_field_plane_level."
    )

    def process(self, field: DataField) -> tuple:
        data = field.data.copy()
        yres, xres = data.shape

        # Normalised coordinate grids in [0, 1]
        x = np.linspace(0.0, 1.0, xres)
        y = np.linspace(0.0, 1.0, yres)
        xx, yy = np.meshgrid(x, y)

        # Design matrix: [1, x, y]  shape (N, 3)
        A = np.column_stack([
            np.ones(xres * yres),
            xx.ravel(),
            yy.ravel(),
        ])
        z = data.ravel()

        # Least-squares: solve A @ [pa, pbx, pby] = z
        coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
        pa, pbx, pby = coeffs

        plane = (pa + pbx * xx + pby * yy)
        return (field.replace(data=data - plane),)


# ---------------------------------------------------------------------------
# PolyLevelField
# ---------------------------------------------------------------------------

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
    CATEGORY = "level"
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

        # Build Vandermonde-style design matrix with all monomials x^i * y^j
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


# ---------------------------------------------------------------------------
# FixZero
# ---------------------------------------------------------------------------

@register_node(display_name="Fix Zero")
class FixZero:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["min", "mean", "median"],),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("zeroed",)
    FUNCTION = "process"
    CATEGORY = "level"
    DESCRIPTION = (
        "Shift data so that the minimum (or mean/median) is zero. "
        "Equivalent to fix_zero in Gwyddion's level.c."
    )

    def process(self, field: DataField, method: str) -> tuple:
        data = field.data.copy()
        if method == "min":
            data -= data.min()
        elif method == "mean":
            data -= data.mean()
        elif method == "median":
            data -= np.median(data)
        else:
            raise ValueError(f"Unknown method: {method}")
        return (field.replace(data=data),)
