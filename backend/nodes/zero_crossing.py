"""Zero crossing detection — edge detection via LoG zero crossings."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_laplace

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Zero Crossing")
class ZeroCrossing:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma": ("FLOAT", {"default": 2.0, "min": 0.5, "max": 20.0, "step": 0.1}),
                "threshold": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'edges'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect edges by finding zero crossings of the Laplacian of Gaussian "
        "(LoG). Sigma controls the Gaussian smoothing scale. Threshold filters "
        "out weak edges (relative to the LoG range). "
    )

    KEYWORDS = ("edge", "laplacian of gaussian", "log", "marr hildreth", "contour", "boundary")

    def process(self, field: DataField, sigma: float, threshold: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Compute LoG
        log = gaussian_laplace(data, sigma=sigma)

        # Find zero crossings: adjacent pixels with opposite signs
        edges = np.zeros_like(data)

        # Horizontal crossings
        sign_diff_x = log[:, :-1] * log[:, 1:]
        cross_x = sign_diff_x < 0
        strength_x = np.abs(log[:, :-1] - log[:, 1:])

        # Vertical crossings
        sign_diff_y = log[:-1, :] * log[1:, :]
        cross_y = sign_diff_y < 0
        strength_y = np.abs(log[:-1, :] - log[1:, :])

        # Apply threshold
        max_strength = max(strength_x.max(), strength_y.max(), 1e-30)
        edges[:, :-1] += cross_x & (strength_x > threshold * max_strength)
        edges[:-1, :] += cross_y & (strength_y > threshold * max_strength)

        result = (edges > 0).astype(np.float64)
        return (field.replace(data=result, si_unit_z=""),)
