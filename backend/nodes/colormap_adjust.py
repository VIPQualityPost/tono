from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import COLORMAPS, DataField, resolve_colormap_input


@register_node(display_name="Colormap Adjust")
class ColormapAdjust:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "colormap": (["auto", *list(COLORMAPS)], {
                    "default": "auto",
                    "hide_when_input_connected": "colormap_map",
                }),
                "offset": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.05, "max": 4.0, "step": 0.01}),
                "auto": ("BUTTON", {"label": "Auto", "set_widgets": {"offset": 0.0, "scale": 1.0}}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Adjust how a DATA_FIELD maps into its colormap without changing the underlying data. "
        "offset and scale operate in normalized display coordinates; Auto resets to the full data range. "
        "The colormap dropdown (or a connected Color Map) selects the applied ramp: 'auto' keeps the "
        "field's current colormap."
    )

    KEYWORDS = ("colormap", "palette", "contrast", "offset", "scale", "display", "lut")

    def process(
        self,
        field: DataField,
        colormap: str = "auto",
        offset: float = 0.0,
        scale: float = 1.0,
        colormap_map=None,
    ) -> tuple:
        scale = float(scale)
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError("Scale must be a positive number.")
        resolved = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=field.colormap,
            default="viridis",
        )
        return (field.replace(
            display_offset=float(offset),
            display_scale=scale,
            colormap=resolved,
        ),)
