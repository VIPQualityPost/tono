"""SEM simulation — scanning electron microscopy image simulation."""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import gaussian_filter, shift

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="SEM Simulation")
class SEMSimulation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["integration", "monte_carlo"],),
                "sigma": ("FLOAT", {
                    "default": 3.0, "min": 0.1, "max": 50.0, "step": 0.1,
                }),
                "n_samples": ("INT", {
                    "default": 100, "min": 10, "max": 10000,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Simulates scanning electron microscopy imaging from topography data. "
        "The integration method computes the surface slope (gradient magnitude) "
        "and applies Gaussian smoothing to approximate the secondary electron "
        "yield, modelling the beam interaction volume. The Monte Carlo method "
        "stochastically samples neighbour height differences weighted by a "
        "Gaussian kernel to estimate the local surface visibility, producing "
        "edge-enhanced contrast similar to real SEM images."
    )

    KEYWORDS = ("electron", "secondary electron", "synthetic", "render", "shading", "slope")

    def process(self, field: DataField, method: str, sigma: float,
                n_samples: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if method == "integration":
            result = self._integration(data, field.dx, field.dy, sigma)
        elif method == "monte_carlo":
            result = self._monte_carlo(data, sigma, n_samples)
        else:
            raise ValueError(f"Unknown SEM simulation method: {method!r}")

        return (field.replace(data=result, si_unit_z=""),)

    # ------------------------------------------------------------------

    @staticmethod
    def _integration(data: np.ndarray, dx: float, dy: float,
                     sigma: float) -> np.ndarray:
        """Gradient-magnitude method with Gaussian interaction smoothing."""
        dz_dy, dz_dx = np.gradient(data, dy, dx)
        # SEM signal ~ local slope (edge enhancement)
        slope = np.sqrt(dz_dx**2 + dz_dy**2)
        # Gaussian blur to simulate beam interaction volume
        result = gaussian_filter(slope, sigma=sigma)
        return result

    @staticmethod
    def _monte_carlo(data: np.ndarray, sigma: float,
                     n_samples: int) -> np.ndarray:
        """Stochastic height-difference sampling with Gaussian weighting."""
        rng = np.random.default_rng(42)
        result = np.zeros_like(data)

        for _ in range(n_samples):
            dx_off = rng.normal(0, sigma)
            dy_off = rng.normal(0, sigma)
            dist = math.sqrt(dx_off**2 + dy_off**2)
            if dist > 0:
                shifted = shift(data, [dy_off, dx_off], mode='reflect')
                weight = math.exp(-(dx_off**2 + dy_off**2) / (2 * sigma**2))
                result += weight * (data - shifted) / dist

        result /= n_samples
        return result
