from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, LineData


@register_node(display_name="Slope Distribution")
class SlopeDistribution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "distribution": (["theta", "phi", "gradient"],),
                "n_bins": ("INT", {"default": 90, "min": 10, "max": 1000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('LINE', 'distribution'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the angular slope distribution of a DATA_FIELD surface. "
        "'theta' is the inclination angle (0–max°), probability density (1/deg); "
        "'phi' is the azimuthal slope direction (0–360°), weighted by slope² (z/xy)²; "
        "'gradient' is the gradient magnitude distribution, probability density (1/(z/xy)). "
    )

    def process(self, field: DataField, distribution: str, n_bins: int) -> tuple:
        from backend.nodes.surface_common import physical_sobel_gradient, slope_unit as _slope_unit

        gx, gy = physical_sobel_gradient(field)
        gx = gx.ravel()
        gy = gy.ravel()

        su = _slope_unit(field)

        if distribution == "phi":
            return self._phi(gx, gy, n_bins, su)
        elif distribution == "theta":
            return self._theta(gx, gy, n_bins)
        elif distribution == "gradient":
            return self._gradient(gx, gy, n_bins, su)
        else:
            raise ValueError(f"Unknown distribution type: {distribution!r}. "
                             f"Choose from: theta, phi, gradient")

    # ------------------------------------------------------------------
    # phi: azimuthal angle distribution, weighted by slope² (slope_dist.c:430-466)
    # phi = atan2(gy, -gx), canonicalized to [0, 2π); bin weight = gx²+gy²
    # ------------------------------------------------------------------
    def _phi(self, gx, gy, n_bins, slope_unit):
        phi = np.arctan2(gy, -gx)
        phi = phi % (2.0 * np.pi)  # canonicalize to [0, 2π)
        weights = gx ** 2 + gy ** 2

        bin_edges = np.linspace(0.0, 2.0 * np.pi, n_bins + 1)
        counts = np.zeros(n_bins)
        idx = np.clip(np.floor(n_bins * phi / (2.0 * np.pi)).astype(int), 0, n_bins - 1)
        np.add.at(counts, idx, weights)

        centers_deg = np.degrees(0.5 * (bin_edges[:-1] + bin_edges[1:]))
        y_unit = f"({slope_unit})^2" if slope_unit else ""
        return (LineData(data=counts, x_axis=centers_deg, x_unit="deg", y_unit=y_unit),)

    # ------------------------------------------------------------------
    # theta: inclination angle in degrees, normalized probability density (slope_dist.c:468-513)
    # theta = (180/π)·atan(|gradient|); normalized by size/(nc·max)
    # ------------------------------------------------------------------
    def _theta(self, gx, gy, n_bins):
        theta = np.degrees(np.arctan(np.hypot(gx, gy)))
        max_theta = float(theta.max()) if theta.size > 0 else 90.0
        if max_theta == 0.0:
            max_theta = 90.0

        bin_edges = np.linspace(0.0, max_theta, n_bins + 1)
        counts = np.zeros(n_bins)
        idx = np.clip(np.floor(n_bins * theta / max_theta).astype(int), 0, n_bins - 1)
        np.add.at(counts, idx, 1)

        nc = len(theta)
        if nc > 0 and max_theta > 0:
            counts = counts * (n_bins / (nc * max_theta))

        centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        return (LineData(data=counts, x_axis=centers, x_unit="deg", y_unit="1/deg"),)

    # ------------------------------------------------------------------
    # gradient: magnitude distribution, normalized probability density (slope_dist.c:515-560)
    # normalized by size/(nc·max)
    # ------------------------------------------------------------------
    def _gradient(self, gx, gy, n_bins, slope_unit):
        grad = np.hypot(gx, gy)
        max_grad = float(grad.max()) if grad.size > 0 else 1.0
        if max_grad == 0.0:
            max_grad = 1.0

        bin_edges = np.linspace(0.0, max_grad, n_bins + 1)
        counts = np.zeros(n_bins)
        idx = np.clip(np.floor(n_bins * grad / max_grad).astype(int), 0, n_bins - 1)
        np.add.at(counts, idx, 1)

        nc = len(grad)
        if nc > 0 and max_grad > 0:
            counts = counts * (n_bins / (nc * max_grad))

        centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        y_unit = f"1/({slope_unit})" if slope_unit else ""
        return (LineData(data=counts, x_axis=centers, x_unit=slope_unit, y_unit=y_unit),)
