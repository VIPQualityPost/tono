from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, encode_preview
from backend.nodes.helpers import _mask_overlay


@register_node(display_name="Mask Combine")
class MaskCombine:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask_a": ("IMAGE",),
                "mask_b": ("IMAGE",),
                "operation": (["and", "or", "xor", "subtract"],),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Combine two binary masks with a boolean operation. "
        "AND keeps overlap, OR merges, XOR keeps non-overlapping regions, "
        "subtract removes mask_b from mask_a."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, mask_a: np.ndarray, mask_b: np.ndarray, operation: str,
                field: DataField | None = None) -> tuple:
        a = mask_a > 127
        b = mask_b > 127

        if operation == "and":
            result = a & b
        elif operation == "or":
            result = a | b
        elif operation == "xor":
            result = a ^ b
        elif operation == "subtract":
            result = a & ~b
        else:
            raise ValueError(f"Unknown mask operation: {operation}")

        out = result.astype(np.uint8) * 255

        if field is not None and MaskCombine._broadcast_fn is not None:
            overlay = _mask_overlay(field, out)
            MaskCombine._broadcast_fn(
                MaskCombine._current_node_id, encode_preview(overlay),
            )

        return (out,)
