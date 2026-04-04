from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask, mask_to_bool, emit_mask_preview


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

    def process(self, mask: np.ndarray, field: DataField | None = None) -> tuple:
        out = bool_to_mask(~mask_to_bool(mask))

        emit_mask_preview(field, out)

        return (out,)
