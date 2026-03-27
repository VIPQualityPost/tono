from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, datafield_to_uint8, encode_preview
from backend.nodes.helpers import _parse_mask_strokes, _rasterize_mask


@register_node(display_name="Draw Mask")
class DrawMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "pen_size": ("INT", {"default": 12, "min": 1, "max": 128, "step": 1}),
                "invert": ("BOOLEAN", {"default": False}),
                "clear_mask": ("BUTTON", {"label": "Clear Mask", "set_widgets": {"mask_paths": "[]"}}),
                "mask_paths": ("STRING", {"default": "[]", "hidden": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Paint a binary mask directly over an image preview. "
        "Pen size controls newly drawn strokes, the overlay lets you clear the mask, "
        "and invert flips the final binary output."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(self, field: DataField, pen_size: int, invert: bool, mask_paths: str) -> tuple:
        strokes = _parse_mask_strokes(mask_paths)
        mask = _rasterize_mask(field.xres, field.yres, strokes, pen_size)
        if invert:
            mask = np.where(mask > 127, np.uint8(0), np.uint8(255))

        emit_overlay({
            "kind": "mask_paint",
            "section_title": "Mask",
            "image": encode_preview(datafield_to_uint8(field, "gray")),
            "image_width": field.xres,
            "image_height": field.yres,
            "invert": bool(invert),
        })

        return (mask,)
