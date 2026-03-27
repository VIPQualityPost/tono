from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import (
    DataField,
    ImageData,
    _apply_markup_overlay,
    encode_preview,
    image_metadata,
    image_to_uint8,
    render_datafield_preview,
)
from backend.nodes.helpers import _parse_markup_shapes, _normalize_markup_color


@register_node(display_name="Markup")
class Markup:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("ANNOTATION_SOURCE", {"label": "Input"}),
                "shape": (["line", "rectangle", "circle", "arrow"], {"default": "line"}),
                "stroke_color": ("STRING", {"default": "#ffd54f", "color_picker": True}),
                "stroke_width": ("INT", {"default": 3, "min": 1, "max": 64, "step": 1}),
                "clear_shapes": ("BUTTON", {"label": "Clear Shapes", "set_widgets": {"markup_shapes": "[]"}}),
                "markup_shapes": ("STRING", {"default": "[]", "hidden": True}),
            }
        }

    RETURN_TYPES = ("ANNOTATION_SOURCE",)
    RETURN_NAMES = ("Output",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Draw simple vector markup over a DATA_FIELD without flattening the underlying data, "
        "or rasterize markup directly onto an IMAGE."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self,
        input,
        shape: str,
        stroke_color: str,
        stroke_width: int,
        markup_shapes: str,
    ) -> tuple:
        shapes = _parse_markup_shapes(markup_shapes)
        markup_spec = {
            "kind": "markup",
            "shapes": shapes,
        }

        if isinstance(input, DataField):
            out = input.replace(
                overlays=[
                    *input.overlays,
                    markup_spec,
                ],
            )
            preview_base = render_datafield_preview(input, input.colormap)
        else:
            preview_base = image_to_uint8(input)
            out = ImageData(
                _apply_markup_overlay(preview_base, None, markup_spec),
                metadata=image_metadata(input),
            )

        if Markup._broadcast_overlay_fn is not None:
            Markup._broadcast_overlay_fn(
                Markup._current_node_id,
                {
                    "kind": "markup",
                    "section_title": "Markup",
                    "image": encode_preview(preview_base),
                    "shape": str(shape),
                    "stroke_color": _normalize_markup_color(stroke_color),
                    "stroke_width": max(1, int(stroke_width)),
                },
            )

        return (out,)
