"""Level grains — shift individual grain regions to a common baseline."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Level Grains")
class LevelGrains:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "reference": (["mean", "median", "minimum"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Shift individual grain regions (from a mask) so they all share a "
        "common baseline. Uses the selected reference statistic (mean, median, "
        "or minimum) per grain to compute the offset. "
        "Useful for consistent grain height comparisons. "
    )

    KEYWORDS = ("align", "baseline", "flatten", "particle")

    def process(self, field: DataField, mask: np.ndarray, reference: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64).copy()
        grain_mask = mask_to_bool(mask)
        labeled, n_grains = label(grain_mask.astype(np.int32))

        if n_grains == 0:
            return (field.replace(data=data),)

        # Compute reference value for each grain
        refs = []
        for gid in range(1, n_grains + 1):
            pixels = data[labeled == gid]
            if len(pixels) == 0:
                refs.append(0.0)
                continue
            if reference == "mean":
                refs.append(float(pixels.mean()))
            elif reference == "median":
                refs.append(float(np.median(pixels)))
            else:  # minimum
                refs.append(float(pixels.min()))

        # Target: global reference across all grains
        target = float(np.mean(refs))

        # Shift each grain
        for gid in range(1, n_grains + 1):
            grain_pixels = labeled == gid
            offset = target - refs[gid - 1]
            data[grain_pixels] += offset

        return (field.replace(data=data),)
