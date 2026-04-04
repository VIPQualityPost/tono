"""Displacement field — distort images using displacement fields."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Displacement Field")
class DisplacementField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["gaussian_1d", "gaussian_2d", "tear"], {"default": "gaussian_1d"}),
                "sigma": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 100.0, "step": 0.1}),
                "tau": ("FLOAT", {"default": 20.0, "min": 1.0, "max": 500.0, "step": 1.0}),
                "density": ("FLOAT", {
                    "default": 0.02,
                    "min": 0.001,
                    "max": 0.25,
                    "step": 0.001,
                    "show_when_widget_value": {"method": ["tear"]},
                }),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Distort an image using synthetic displacement fields. "
        "Supports 1D Gaussian (row-correlated), 2D Gaussian (fully correlated), "
        "and tear (random horizontal tear lines) distortion modes. "
        "Equivalent to Gwyddion's displfield.c module."
    )

    def process(
        self,
        field: DataField,
        method: str,
        sigma: float,
        tau: float,
        density: float,
        seed: int,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        rng = np.random.default_rng(seed)

        y_grid, x_grid = np.mgrid[:yres, :xres].astype(np.float64)

        if method == "gaussian_1d":
            dx_1d = gaussian_filter1d(rng.standard_normal(xres), tau) * sigma
            dx = np.tile(dx_1d, (yres, 1))
            dy = np.zeros_like(dx)

        elif method == "gaussian_2d":
            dx = gaussian_filter(rng.standard_normal((yres, xres)), tau) * sigma
            dy = gaussian_filter(rng.standard_normal((yres, xres)), tau) * sigma

        elif method == "tear":
            dx = np.zeros((yres, xres), dtype=np.float64)
            dy = np.zeros((yres, xres), dtype=np.float64)

            # Select tear rows based on density
            tear_mask = rng.random(yres) < density
            tear_rows = np.nonzero(tear_mask)[0]

            for row in tear_rows:
                offset = rng.standard_normal() * sigma
                # Apply offset that decays exponentially away from the tear line
                for i in range(yres):
                    dist = abs(i - row)
                    dx[i] += offset * np.exp(-dist / max(tau, 1.0))

            # Smooth the displacement to avoid sharp edges
            for i in range(yres):
                dx[i] = gaussian_filter1d(dx[i], tau / 4.0)

        else:
            raise ValueError(f"Unknown method: {method!r}")

        coords_y = y_grid + dy
        coords_x = x_grid + dx
        result = map_coordinates(data, [coords_y, coords_x], mode='reflect', order=3)

        return (field.replace(data=result),)
