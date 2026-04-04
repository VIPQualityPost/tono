from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.nodes.helpers import mask_to_bool, bool_to_mask


@register_node(display_name="Grain Filter")
class GrainFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "min_area": ("INT", {"default": 10, "min": 0, "max": 1000000, "step": 1}),
                "max_area": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "remove_border": ("BOOLEAN", {"default": False}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'filtered_mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Remove grains from a binary mask based on size and border contact. "
        "'min_area': discard grains smaller than this many pixels (removes specks). "
        "'max_area': discard grains larger than this many pixels (0 = no limit). "
        "'remove_border': discard any grain that touches the image edge. "
    )

    def process(
        self,
        mask: np.ndarray,
        min_area: int,
        max_area: int,
        remove_border: bool,
    ) -> tuple:
        from scipy.ndimage import label

        binary = mask_to_bool(mask)
        labeled, n_grains = label(binary)

        # Build per-grain keep table (index 0 = background, always False)
        keep = np.zeros(n_grains + 1, dtype=bool)

        for gid in range(1, n_grains + 1):
            grain = labeled == gid
            area = int(grain.sum())

            if area < min_area:
                continue
            if max_area > 0 and area > max_area:
                continue
            if remove_border and _touches_border(grain):
                continue

            keep[gid] = True

        result = keep[labeled]
        return (bool_to_mask(result),)


def _touches_border(grain: np.ndarray) -> bool:
    return (
        grain[0, :].any()
        or grain[-1, :].any()
        or grain[:, 0].any()
        or grain[:, -1].any()
    )
