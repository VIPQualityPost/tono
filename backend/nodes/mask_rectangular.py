from __future__ import annotations

import numpy as np

from backend.data_types import DataField, datafield_to_uint8, encode_preview
from backend.execution_context import emit_overlay
from backend.node_registry import register_node
from backend.nodes.helpers import bool_to_mask, coerce_physical_square


@register_node(display_name="Rectangular Mask")
class RectangularMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "x1": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "square": ("BOOLEAN", {"default": False}),
                "invert": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "corner_a": ("COORD",),
                "corner_b": ("COORD",),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a binary mask covering a rectangular region of a DATA_FIELD, "
        "defined by two draggable corners on the preview. Useful for selecting "
        "a region of interest without cropping the image. When 'square' is on, "
        "the mask is coerced to a physical square (the longer side shrinks to "
        "match the shorter, anchored at the top-left corner). When 'invert' is "
        "on, the mask covers everything outside the rectangle instead. "
        "Incoming COORD inputs can lock either corner."
    )

    KEYWORDS = ("roi", "region", "rectangle", "square", "box", "selection", "crop mask")

    def process(
        self,
        field: DataField,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        square: bool,
        invert: bool,
        corner_a=None,
        corner_b=None,
    ) -> tuple:
        if corner_a is not None:
            x1, y1 = float(corner_a[0]), float(corner_a[1])
        if corner_b is not None:
            x2, y2 = float(corner_b[0]), float(corner_b[1])

        x1 = float(np.clip(x1, 0.0, 1.0))
        y1 = float(np.clip(y1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 1.0))
        y2 = float(np.clip(y2, 0.0, 1.0))

        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)

        if square:
            left, top, right, bottom = coerce_physical_square(
                left, top, right, bottom, field.xreal, field.yreal,
            )

        emit_overlay({
            "kind": "crop_box",
            "section_title": "Preview",
            "image": encode_preview(datafield_to_uint8(field, field.colormap)),
            "x1": left,
            "y1": top,
            "x2": right,
            "y2": bottom,
            "xreal": float(field.xreal),
            "yreal": float(field.yreal),
            "a_locked": corner_a is not None,
            "b_locked": corner_b is not None,
        })

        px0 = int(np.floor(left * field.xres))
        py0 = int(np.floor(top * field.yres))
        px1 = int(np.ceil(right * field.xres))
        py1 = int(np.ceil(bottom * field.yres))

        px0 = min(max(px0, 0), field.xres)
        py0 = min(max(py0, 0), field.yres)
        px1 = min(max(px1, px0), field.xres)
        py1 = min(max(py1, py0), field.yres)

        binary = np.zeros((field.yres, field.xres), dtype=bool)
        binary[py0:py1, px0:px1] = True
        if invert:
            binary = ~binary

        mask = bool_to_mask(binary)

        return (mask,)
