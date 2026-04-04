"""Grain edge detection — detect grain boundaries using Laplacian edge detection."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask


@register_node(display_name="Grain Edge")
class GrainEdge:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "width": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'edge_mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect grain boundaries from a binary grain mask. Outputs a mask "
        "of pixels at grain edges (where grain meets non-grain). Width "
        "controls the boundary thickness in pixels. "
    )

    KEYWORDS = ("boundary", "outline", "perimeter", "contour")

    def process(self, field: DataField, mask: np.ndarray, width: int) -> tuple:
        grain = mask_to_bool(mask)

        # Find boundary: grain pixels with at least one non-grain 4-neighbour
        padded = np.pad(grain, 1, mode='constant', constant_values=False)
        interior = (padded[:-2, 1:-1] & padded[2:, 1:-1] &
                    padded[1:-1, :-2] & padded[1:-1, 2:])
        boundary = grain & ~interior

        # Expand boundary by width
        if width > 1:
            from scipy.ndimage import binary_dilation
            struct = np.ones((2 * width - 1, 2 * width - 1), dtype=bool)
            boundary = binary_dilation(boundary, structure=struct) & grain

        return (bool_to_mask(boundary),)
