from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Colormap Adjust")
class ColormapAdjust:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "offset": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.05, "max": 4.0, "step": 0.01}),
                "auto": ("BUTTON", {"label": "Auto", "set_widgets": {"offset": 0.0, "scale": 1.0}}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Adjust how a DATA_FIELD maps into its colormap without changing the underlying data. "
        "offset and scale operate in normalized display coordinates; Auto resets to the full data range."
    )

    def process(self, field: DataField, offset: float, scale: float) -> tuple:
        scale = float(scale)
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError("Scale must be a positive number.")
        return (field.replace(display_offset=float(offset), display_scale=scale),)
