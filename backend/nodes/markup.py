from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, encode_preview
from backend.nodes.helpers import _parse_markup_shapes, _normalize_markup_color


@register_node(display_name="Markup")
class Markup:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shape": (["line", "rectangle", "circle", "arrow"], {"default": "line"}),
                "stroke_color": ("STRING", {"default": "#ffd54f", "color_picker": True}),
                "stroke_width": ("INT", {"default": 3, "min": 1, "max": 64, "step": 1}),
                "clear_shapes": ("BUTTON", {"label": "Clear Shapes", "set_widgets": {"markup_shapes": "[]"}}),
                "markup_shapes": ("STRING", {"default": "[]", "hidden": True}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("annotated",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Draw simple vector markup over a DATA_FIELD without flattening the underlying data. "
        "Choose a shape mode, colour, and stroke width, then drag directly on the preview to place lines, rectangles, circles, or arrows."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self,
        field: DataField,
        shape: str,
        stroke_color: str,
        stroke_width: int,
        markup_shapes: str,
    ) -> tuple:
        shapes = _parse_markup_shapes(markup_shapes)
        out = field.replace(
            overlays=[
                *field.overlays,
                {
                    "kind": "markup",
                    "shapes": shapes,
                },
            ],
        )

        if Markup._broadcast_overlay_fn is not None:
            Markup._broadcast_overlay_fn(
                Markup._current_node_id,
                {
                    "kind": "markup",
                    "section_title": "Markup",
                    "image": encode_preview(datafield_to_uint8(field, field.colormap)),
                    "shape": str(shape),
                    "stroke_color": _normalize_markup_color(stroke_color),
                    "stroke_width": max(1, int(stroke_width)),
                },
            )

        return (out,)
