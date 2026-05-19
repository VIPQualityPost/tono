"""Sphere Revolve — subtract a spherical cap background."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

from backend.node_registry import register_node
from backend.data_types import DataField


def _sphere_kernel(radius: int) -> np.ndarray:
    """Build a 2D spherical cap kernel."""
    half = min(radius, 512)
    i = np.arange(-half, half + 1, dtype=np.float64)
    ii, jj = np.meshgrid(i, i)
    r2 = (ii ** 2 + jj ** 2) / (radius ** 2)
    r2 = np.clip(r2, 0.0, 1.0)
    return 1.0 - np.sqrt(1.0 - r2)


@register_node(display_name="Sphere Revolve")
class SphereRevolve:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "radius": ("INT", {"default": 20, "min": 1, "max": 500, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('DATA_FIELD', 'background'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Subtract a spherical cap background. A sphere of the given radius "
        "is rolled under the surface, and the envelope it traces is "
        "subtracted as the background."
    )

    KEYWORDS = ("sphere", "revolve", "spherical", "background", "level")

    def process(self, field: DataField, radius: int = 20) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        kernel = _sphere_kernel(radius)
        half = kernel.shape[0] // 2

        # Suppress deep outliers
        window = max(1, half // 2)
        local_mean = uniform_filter(data, size=2 * window + 1, mode='nearest')
        local_sq = uniform_filter(data ** 2, size=2 * window + 1, mode='nearest')
        local_rms = np.sqrt(np.maximum(local_sq - local_mean ** 2, 0.0))
        threshold = local_mean - 2.5 * np.maximum(local_rms, 1e-30)
        clipped = np.maximum(data, threshold)

        padded = np.pad(clipped, half, mode='edge')
        bg = np.full_like(data, np.inf)

        ks = kernel.shape[0]
        for di in range(ks):
            for dj in range(ks):
                k_val = kernel[di, dj]
                if k_val >= 1.0:
                    continue
                shifted = padded[di:di + yres, dj:dj + xres] - k_val
                bg = np.minimum(bg, shifted)

        return (field.replace(data=data - bg), field.replace(data=bg))
