from __future__ import annotations

import numpy as np
from scipy.ndimage import grey_erosion

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Tip Deconvolution")
class TipDeconvolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "tip": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'surface'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Reconstruct the true surface from a tip-broadened measured image. "
        "Uses morphological grey erosion (Villarrubia algorithm): "
        "  mytip = flip(tip) − max(flip(tip))   [max shifted to 0] "
        "  surface[y,x] = min_{dy,dx}[image[y+dy, x+dx] − mytip[dy,dx]] "
        "Connect the tip output from a TipModel node. "
        "The tip pixel size must match the image pixel size. "
    )

    def process(self, field: DataField, tip: DataField) -> tuple:
        # Gwyddion gwy_tip_erosion:
        #   mytip = flip(tip) − max(flip(tip))   (values ≤ 0, apex = 0)
        #   result[y,x] = min_{ty,tx}[surface[y+ty, x+tx] − mytip[ty,tx]]
        tip_flipped = np.flipud(np.fliplr(tip.data))
        mytip = tip_flipped - tip_flipped.max()     # shift so max = 0

        result = grey_erosion(field.data, structure=mytip)
        return (field.replace(data=result),)
