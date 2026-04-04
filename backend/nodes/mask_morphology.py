from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import _mask_structure, mask_to_bool, bool_to_mask, emit_mask_preview


@register_node(display_name="Mask Morphology")
class MaskMorphology:
    """
    Morphological operations on binary masks.
    """
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "operation": (["dilate", "erode", "open", "close"],),
                "radius": ("INT", {"default": 1, "min": 1, "max": 50, "step": 1}),
                "shape": (["disk", "square"],),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply morphological operations to a binary mask. "
        "Dilate expands regions, erode shrinks them, "
        "open (erode then dilate) removes small spots, "
        "close (dilate then erode) fills small holes. "
    )

    def process(self, mask: np.ndarray, operation: str, radius: int, shape: str,
                field: DataField | None = None) -> tuple:
        from scipy.ndimage import binary_closing, binary_dilation, binary_erosion, binary_opening

        binary = mask_to_bool(mask)
        struct = _mask_structure(radius, shape)

        if operation == "dilate":
            result = binary_dilation(binary, structure=struct)
        elif operation == "erode":
            result = binary_erosion(binary, structure=struct)
        elif operation == "open":
            result = binary_opening(binary, structure=struct)
        elif operation == "close":
            result = binary_closing(binary, structure=struct)
        else:
            raise ValueError(f"Unknown morphological operation: {operation}")

        out = bool_to_mask(result)

        emit_mask_preview(field, out)

        return (out,)
