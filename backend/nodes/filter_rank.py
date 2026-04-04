"""Rank filter — general k-th rank filter for morphological operations."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import percentile_filter, minimum_filter, maximum_filter, median_filter

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Rank Filter")
class RankFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "operation": (["erosion", "dilation", "median", "percentile"],
                              {"default": "median"}),
                "radius": ("INT", {"default": 3, "min": 1, "max": 50, "step": 1}),
                "percentile": ("FLOAT", {"default": 50.0, "min": 0.0, "max": 100.0, "step": 1.0}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply rank-based morphological filtering. Erosion selects the local "
        "minimum (shrinks features), dilation the local maximum (grows features), "
        "median the 50th percentile. Custom percentile allows any rank. "
    )

    def process(self, field: DataField, operation: str, radius: int,
                percentile: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        size = 2 * radius + 1

        if operation == "erosion":
            result = minimum_filter(data, size=size)
        elif operation == "dilation":
            result = maximum_filter(data, size=size)
        elif operation == "median":
            result = median_filter(data, size=size)
        elif operation == "percentile":
            result = percentile_filter(data, percentile=percentile, size=size)
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        return (field.replace(data=result),)
