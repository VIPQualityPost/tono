from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_warning
from backend.data_types import (
    COLORMAPS,
    DataField,
    ImageData,
    _apply_annotation_overlay_from_context,
    _annotation_context_from_image,
    image_to_uint8,
    normalize_font_spec,
    resolve_colormap_input,
)


@register_node(display_name="Annotations")
class Annotations:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("ANNOTATION_SOURCE", {
                    "label": "Input",
                    "accepted_types": ["DATA_FIELD", "IMAGE"],
                }),
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

    OUTPUTS = (
        ('ANNOTATION_SOURCE', 'output'),
    )
    FUNCTION = "render"

    DESCRIPTION = (
        "Attach optional publication-style annotations to a DATA_FIELD without flattening the raw data, "
        "or annotate an IMAGE that carries viewport metadata from View3D."
    )

    KEYWORDS = ("scale bar", "legend", "colorbar", "publication")

    def render(
        self,
        input,
        colormap: str,
        show_scale_bar: bool,
        show_color_map: bool,
        text_size: float = 1.0,
        colormap_map=None,
        font=None,
    ) -> tuple:
        annotation_spec = {
            "kind": "annotation",
            "show_scale_bar": bool(show_scale_bar),
            "show_color_map": bool(show_color_map),
            "text_size": float(np.clip(text_size, 6.0, 96.0)) if np.isfinite(text_size) else 14.0,
            "font": normalize_font_spec(font),
        }

        if isinstance(input, DataField):
            resolved_colormap = resolve_colormap_input(
                colormap,
                colormap_input=colormap_map,
                inherited=input.colormap,
                default="gray",
            )
            out = input.replace(
                colormap=resolved_colormap,
                overlays=[
                    *input.overlays,
                    annotation_spec,
                ],
            )
            return (out,)

        context = _annotation_context_from_image(input)
        if context is None:
            emit_warning(
                "Annotations image input has no scale metadata, so scale bar and color-map legend cannot be added."
            )
            return (ImageData(image_to_uint8(input)),)

        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=context.get("colormap"),
            default="gray",
        )
        context["colormap"] = resolved_colormap
        missing_features = []
        xreal = context.get("xreal")
        if bool(show_scale_bar) and not (isinstance(xreal, (int, float)) and np.isfinite(float(xreal)) and float(xreal) > 0 and str(context.get("si_unit_xy", "")).strip()):
            missing_features.append("scale bar")
        if bool(show_color_map):
            legend_values = (context.get("legend_min"), context.get("legend_mid"), context.get("legend_max"))
            has_legend_values = all(
                isinstance(value, (int, float)) and np.isfinite(float(value))
                for value in legend_values
            )
            if not (has_legend_values and str(context.get("legend_unit", "")).strip()):
                missing_features.append("color-map legend")
        if missing_features:
            emit_warning(
                f"Annotations image input is missing metadata for: {', '.join(missing_features)}."
            )
        annotated = _apply_annotation_overlay_from_context(
            image_to_uint8(input),
            context,
            annotation_spec,
        )
        return (ImageData(annotated, metadata={"annotation_context": context}),)
