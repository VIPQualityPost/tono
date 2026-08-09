"""Laplace interpolation — fill masked regions by solving the Laplace equation."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Laplace Interpolation")
class LaplaceInterpolation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "iterations": ("INT", {"default": 500, "min": 10, "max": 10000, "step": 10}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fill masked (missing) regions by solving the Laplace equation with "
        "Dirichlet boundary conditions from surrounding pixels. "
        "Produces a smooth, harmonic interpolation without overshooting. "
    )

    KEYWORDS = ("inpaint", "fill", "hole", "infill", "harmonic")

    def process(self, field: DataField, mask: np.ndarray, iterations: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64).copy()
        hole = mask_to_bool(mask)

        if not hole.any():
            return (field.replace(data=data),)

        # Initialize masked pixels to mean of unmasked neighbors or global mean
        valid_mean = data[~hole].mean() if (~hole).any() else 0.0
        data[hole] = valid_mean

        # Iterative Jacobi relaxation: replace each masked pixel with
        # the mean of its 4-connected neighbors
        padded = np.pad(data, 1, mode='edge')
        hole_padded = np.pad(hole, 1, mode='constant', constant_values=False)

        for _ in range(iterations):
            avg = (padded[:-2, 1:-1] + padded[2:, 1:-1] +
                   padded[1:-1, :-2] + padded[1:-1, 2:]) / 4.0
            padded[1:-1, 1:-1][hole] = avg[hole]

        data = padded[1:-1, 1:-1].copy()
        return (field.replace(data=data),)
