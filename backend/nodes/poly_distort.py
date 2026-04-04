"""Polynomial distortion correction — correct nonlinear scanner distortions."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Polynomial Distortion")
class PolynomialDistortion:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "k1_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "k1_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "k2_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "k2_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "k3_x": ("FLOAT", {"default": 0.0, "min": -0.5, "max": 0.5, "step": 0.001}),
                "k3_y": ("FLOAT", {"default": 0.0, "min": -0.5, "max": 0.5, "step": 0.001}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Correct nonlinear scanner distortions with polynomial coordinate "
        "warping up to cubic order. Coefficients k1 (linear correction), "
        "k2 (quadratic), k3 (cubic) are applied independently to x and y axes. "
    )

    KEYWORDS = ("warp", "scanner", "nonlinear", "cubic", "quadratic", "barrel")

    def process(self, field: DataField,
                k1_x: float, k1_y: float,
                k2_x: float, k2_y: float,
                k3_x: float, k3_y: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Normalised coordinates [-1, 1]
        yy, xx = np.mgrid[:yres, :xres]
        xn = 2.0 * xx / max(xres - 1, 1) - 1.0
        yn = 2.0 * yy / max(yres - 1, 1) - 1.0

        # Apply polynomial distortion (inverse mapping)
        xn_src = xn + k1_x * xn + k2_x * xn**2 + k3_x * xn**3
        yn_src = yn + k1_y * yn + k2_y * yn**2 + k3_y * yn**3

        # Convert back to pixel coordinates
        sx = (xn_src + 1.0) * max(xres - 1, 1) / 2.0
        sy = (yn_src + 1.0) * max(yres - 1, 1) / 2.0

        result = map_coordinates(data, [sy, sx], order=1, mode='nearest')
        return (field.replace(data=result),)
