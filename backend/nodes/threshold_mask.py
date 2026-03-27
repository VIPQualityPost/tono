from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_preview
from backend.data_types import DataField, encode_preview
from backend.nodes.helpers import _mask_overlay


@register_node(display_name="Threshold Mask")
class ThresholdMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["otsu", "absolute", "relative"],),
                "threshold": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "direction": (["above", "below"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a binary mask by thresholding data. "
        "Otsu automatically finds the optimal threshold. "
        "Equivalent to Gwyddion's threshold and otsu_threshold modules."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, field: DataField, method: str, threshold: float, direction: str) -> tuple:
        data = field.data

        if method == "otsu":
            from skimage.filters import threshold_otsu
            t = threshold_otsu(data)
        elif method == "absolute":
            t = float(threshold)
        elif method == "relative":
            dmin, dmax = data.min(), data.max()
            t = dmin + float(threshold) * (dmax - dmin)
        else:
            raise ValueError(f"Unknown threshold method: {method}")

        if direction == "above":
            mask = (data >= t).astype(np.uint8) * 255
        else:
            mask = (data < t).astype(np.uint8) * 255

        overlay = _mask_overlay(field, mask)
        emit_preview(encode_preview(overlay))

        return (mask,)
