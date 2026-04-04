"""Median background subtraction — extract and subtract background using local median."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Median Background")
class MedianBackground:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "radius": ("INT", {"default": 20, "min": 2, "max": 500, "step": 1}),
                "output": (["subtracted", "background"], {"default": "subtracted"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract background using a local median filter and subtract it. "
        "The radius controls the filter window size — larger values capture "
        "broader background variations. More robust than polynomial leveling "
        "for surfaces with sparse tall features. "
    )

    KEYWORDS = ("rolling ball", "flatten", "level", "subtract", "baseline")

    def process(self, field: DataField, radius: int, output: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        size = 2 * radius + 1
        background = median_filter(data, size=size)

        if output == "background":
            return (field.replace(data=background),)
        else:
            return (field.replace(data=data - background),)
