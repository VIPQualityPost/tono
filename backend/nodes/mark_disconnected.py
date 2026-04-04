"""Mark disconnected regions — mask topologically isolated surface regions."""

from __future__ import annotations
import numpy as np
from scipy.ndimage import grey_opening, grey_closing
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask, _mask_structure, emit_mask_preview


@register_node(display_name="Mark Disconnected")
class MarkDisconnected:
    """
    Detect topologically disconnected (isolated) surface regions using
    morphological opening/closing to build a defect-free reference, then
    thresholding the residual difference.
    """
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "defect_type": (["positive", "negative", "both"],),
                "radius": ("INT", {"default": 5, "min": 1, "max": 100, "step": 1}),
                "threshold": ("FLOAT", {"default": 0.1, "min": 0.001, "max": 1.0, "step": 0.001}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Mark topologically disconnected (isolated) surface regions. "
        "A morphological opening followed by closing builds a smooth "
        "defect-free reference surface; pixels whose deviation from that "
        "reference exceeds the sensitivity threshold are flagged. "
        "Equivalent to Gwyddion's mark_disconn module."
    )

    def process(self, field: DataField, defect_type: str, radius: int, threshold: float) -> tuple:
        data = field.data.astype(np.float64)

        # Build a disk structuring element for grey-scale morphology.
        struct = _mask_structure(radius, "disk")

        # Morphological opening then closing produces a defect-free reference.
        reference = grey_opening(data, footprint=struct)
        reference = grey_closing(reference, footprint=struct)

        difference = data - reference
        diff_range = difference.max() - difference.min()

        # Avoid division-by-zero on perfectly flat surfaces.
        if diff_range == 0:
            mask = np.zeros(data.shape, dtype=bool)
        else:
            abs_threshold = threshold * diff_range
            if defect_type == "positive":
                mask = difference > abs_threshold
            elif defect_type == "negative":
                mask = difference < -abs_threshold
            else:  # "both"
                mask = np.abs(difference) > abs_threshold

        out = bool_to_mask(mask)
        emit_mask_preview(field, out)
        return (out,)
