from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Invert Value")
class InvertValue:
    """Invert a DATA_FIELD along the z, x, or y axis (Gwyddion `invert_value`)."""

    CATEGORY = "Level & Correct"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mode": (["z", "x", "y"], {"default": "z"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Invert a DATA_FIELD along one axis. Mode z negates heights by reflecting "
        "the values about their mean (so the mean is preserved, matching Gwyddion's "
        "z-invert). Mode x mirrors the field left/right; mode y mirrors it top/bottom. "
        "Physical extents and offsets are preserved."
    )

    KEYWORDS = ("invert", "negate", "mirror", "flip", "reflect")

    def process(self, field: DataField, mode: str) -> tuple:
        mode_name = str(mode).strip().lower()
        if mode_name == "z":
            # gwy_data_field_invert(zflipped=TRUE): data = 2*mean - data
            avg = float(field.data.mean())
            inverted = 2.0 * avg - field.data
        elif mode_name == "x":
            # gwy_data_field_invert(xflipped=TRUE): mirror each row
            inverted = np.fliplr(field.data)
        elif mode_name == "y":
            # gwy_data_field_invert(yflipped=TRUE): swap rows
            inverted = np.flipud(field.data)
        else:
            raise ValueError(f"Unknown invert mode: {mode!r}. Choose from: z, x, y")

        return (field.replace(data=np.asarray(inverted, dtype=np.float64)),)
