from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import COLORMAPS, DataField, normalize_font_spec, resolve_colormap_input


@register_node(display_name="Annotations")
class Annotations:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "colormap": (["auto"] + list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
                "show_scale_bar": ("BOOLEAN", {"default": True}),
                "show_color_map": ("BOOLEAN", {"default": True}),
                "text_size": ("FLOAT", {
                    "default": 14.0,
                    "min": 6.0,
                    "max": 96.0,
                    "step": 1.0,
                }),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
                "font": ("FONT",),
            },
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("annotated",)
    FUNCTION = "render"

    DESCRIPTION = (
        "Attach optional publication-style annotations to a DATA_FIELD without flattening the raw data. "
        "The preview shows a scale bar and/or side colour legend, while downstream field operations keep the underlying AFM values."
    )

    def render(
        self,
        field: DataField,
        colormap: str,
        show_scale_bar: bool,
        show_color_map: bool,
        text_size: float = 1.0,
        colormap_map=None,
        font=None,
    ) -> tuple:
        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=field.colormap,
            default="gray",
        )
        text_size = float(np.clip(text_size, 6.0, 96.0)) if np.isfinite(text_size) else 14.0
        out = field.replace(
            colormap=resolved_colormap,
            overlays=[
                *field.overlays,
                {
                    "kind": "annotation",
                    "show_scale_bar": bool(show_scale_bar),
                    "show_color_map": bool(show_color_map),
                    "text_size": text_size,
                    "font": normalize_font_spec(font),
                },
            ],
        )
        return (out,)
