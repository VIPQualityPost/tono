"""Flatten base — level the flat base of a surface with raised features."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Flatten Base")
class FlattenBase:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "threshold_percentile": ("FLOAT", {"default": 30.0, "min": 5.0, "max": 80.0, "step": 1.0}),
                "poly_degree": ("INT", {"default": 2, "min": 0, "max": 5}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('DATA_FIELD', 'background'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Level the flat base of a surface that has raised features (particles, "
        "grains). Uses a height percentile threshold to identify base pixels, "
        "fits a polynomial to those pixels, and subtracts it. Unlike plane level, "
        "this ignores tall features that would bias the fit. The fitted background "
        "is also provided as a second output. "
    )

    KEYWORDS = ("level", "background", "substrate", "tilt")

    def process(self, field: DataField, threshold_percentile: float, poly_degree: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Identify base pixels: those below the threshold percentile
        threshold = np.percentile(data, threshold_percentile)
        base_mask = data <= threshold

        if base_mask.sum() < max(3, (poly_degree + 1) ** 2):
            # Not enough base pixels, fall back to subtracting the mean
            bg = np.full_like(data, float(data.mean()))
            return (field.replace(data=data - data.mean()), field.replace(data=bg))

        yy, xx = np.mgrid[:yres, :xres]
        x_norm = xx.ravel() / max(xres - 1, 1)
        y_norm = yy.ravel() / max(yres - 1, 1)

        # Build polynomial basis
        cols = []
        for py in range(poly_degree + 1):
            for px in range(poly_degree + 1 - py):
                cols.append(x_norm**px * y_norm**py)
        A_full = np.column_stack(cols)

        # Fit on base pixels only
        base_indices = np.where(base_mask.ravel())[0]
        A_base = A_full[base_indices]
        z_base = data.ravel()[base_indices]
        coeffs, _, _, _ = np.linalg.lstsq(A_base, z_base, rcond=None)

        # Evaluate and subtract
        background = (A_full @ coeffs).reshape(data.shape)
        return (field.replace(data=data - background), field.replace(data=background))
