"""Trimmed mean filter — mean filter excluding extreme percentiles."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Trimmed Mean")
class TrimmedMean:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "radius": ("INT", {"default": 3, "min": 1, "max": 50, "step": 1}),
                "trim_fraction": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 0.45, "step": 0.01}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply a local mean filter that excludes the lowest and highest "
        "fraction of values in each window. More robust than Gaussian for "
        "data with outlier spikes. trim_fraction=0 is a plain mean; "
        "trim_fraction=0.5 approaches the median. "
    )

    KEYWORDS = ("robust", "outlier", "percentile", "smoothing", "denoise", "alpha trimmed")

    def process(self, field: DataField, radius: int, trim_fraction: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        result = np.zeros_like(data)

        padded = np.pad(data, radius, mode='edge')

        for iy in range(yres):
            for ix in range(xres):
                window = padded[iy:iy + 2 * radius + 1, ix:ix + 2 * radius + 1].ravel()
                n = len(window)
                k = int(n * trim_fraction)
                if k > 0:
                    sorted_w = np.sort(window)
                    trimmed = sorted_w[k:n - k]
                else:
                    trimmed = window
                result[iy, ix] = trimmed.mean()

        return (field.replace(data=result),)
