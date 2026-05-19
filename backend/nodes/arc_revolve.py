"""Arc Revolve — subtract a cylindrical arc background."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


def _arc_kernel(radius: int) -> np.ndarray:
    """Build a 1D arc kernel: z = 1 - sqrt(1 - (i/radius)^2)."""
    half = min(radius, 4096)
    i = np.arange(-half, half + 1, dtype=np.float64)
    t = np.clip((i / radius) ** 2, 0.0, 1.0)
    return 1.0 - np.sqrt(1.0 - t)


def _arc_revolve_1d(data: np.ndarray, radius: int) -> np.ndarray:
    """Compute arc-revolve background for each row independently."""
    yres, xres = data.shape
    kernel = _arc_kernel(radius)
    half = len(kernel) // 2
    bg = np.empty_like(data)

    for row in range(yres):
        line = data[row].copy()
        # Suppress deep outliers before fitting
        window = min(half, xres // 2)
        if window > 0:
            from scipy.ndimage import uniform_filter1d
            local_mean = uniform_filter1d(line, size=2 * window + 1, mode='nearest')
            local_sq = uniform_filter1d(line ** 2, size=2 * window + 1, mode='nearest')
            local_rms = np.sqrt(np.maximum(local_sq - local_mean ** 2, 0.0))
            threshold = local_mean - 2.5 * np.maximum(local_rms, 1e-30)
            line = np.maximum(line, threshold)

        # For each pixel, find the lowest position the arc can sit
        padded = np.pad(line, half, mode='edge')
        row_bg = np.full(xres, np.inf)
        for k in range(len(kernel)):
            shifted = padded[k:k + xres] - kernel[k]
            row_bg = np.minimum(row_bg, shifted)
        bg[row] = row_bg

    return bg


@register_node(display_name="Arc Revolve")
class ArcRevolve:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "radius": ("INT", {"default": 20, "min": 1, "max": 1000, "step": 1}),
                "direction": (["horizontal", "vertical", "both"], {"default": "horizontal"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
        ('DATA_FIELD', 'background'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Subtract a cylindrical arc background. A circular arc of the given "
        "radius is rolled under each row (or column), and the envelope it "
        "traces out is subtracted as the background."
    )

    KEYWORDS = ("arc", "revolve", "cylindrical", "background", "level")

    def process(self, field: DataField, radius: int = 20,
                direction: str = "horizontal") -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if direction == "horizontal":
            bg = _arc_revolve_1d(data, radius)
        elif direction == "vertical":
            bg = _arc_revolve_1d(data.T, radius).T
        else:
            bg_h = _arc_revolve_1d(data, radius)
            bg_v = _arc_revolve_1d(data.T, radius).T
            bg = np.minimum(bg_h, bg_v)

        return (field.replace(data=data - bg), field.replace(data=bg))
