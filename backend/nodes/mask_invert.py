from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_preview
from backend.data_types import DataField, encode_preview
from backend.nodes.helpers import _mask_overlay


@register_node(display_name="Mask Invert")
class MaskInvert:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Invert a binary mask — swap masked and unmasked regions."

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, mask: np.ndarray, field: DataField | None = None) -> tuple:
        out = np.where(mask > 127, np.uint8(0), np.uint8(255))

        if field is not None:
            overlay = _mask_overlay(field, out)
            emit_preview(encode_preview(overlay))

        return (out,)
