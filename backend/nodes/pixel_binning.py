"""Pixel binning — downsample by averaging NxN pixel blocks."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Pixel Binning")
class PixelBinning:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "bin_size": ("INT", {"default": 2, "min": 2, "max": 32, "step": 1}),
                "method": (["mean", "sum", "median"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'binned'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Downsample by grouping NxN pixel blocks and computing their mean, "
        "sum, or median. Faster and more controlled than interpolation-based "
        "resampling. Pixels that don't fill a complete block are trimmed. "
    )

    KEYWORDS = ("downsample", "block", "reduce", "coarsen", "average")

    def process(self, field: DataField, bin_size: int, method: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Trim to multiple of bin_size
        ny = (yres // bin_size) * bin_size
        nx = (xres // bin_size) * bin_size
        trimmed = data[:ny, :nx]

        # Reshape into blocks
        blocks = trimmed.reshape(ny // bin_size, bin_size, nx // bin_size, bin_size)

        if method == "mean":
            result = blocks.mean(axis=(1, 3))
        elif method == "sum":
            result = blocks.sum(axis=(1, 3))
        elif method == "median":
            result = np.median(blocks, axis=(1, 3))
        else:
            raise ValueError(f"Unknown method: {method!r}")

        # Update physical dimensions
        new_xreal = field.dx * nx
        new_yreal = field.dy * ny
        return (field.replace(data=result, xreal=new_xreal, yreal=new_yreal),)
