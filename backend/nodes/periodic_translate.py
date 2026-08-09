"""Periodic translate — move data in the XY plane treating it as periodic (Gwyddion ptranslate)."""

from __future__ import annotations

import math

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


def _update_offset(offset: float, res: int, real: float, pxshift: int) -> float:
    """Mirror ptranslate.c's update_offset(): shift the coordinate offset so a
    feature keeps its physical position after a periodic translation, wrapping
    the result into the [-real/2, real/2) range Gwyddion stores offsets in.
    """
    d = real / res if res else 1.0
    val = math.fmod(offset + d * pxshift, real)
    if val < 0.5 * real:
        val += real
    if val > 0.5 * real:
        val -= real
    return float(val)


@register_node(display_name="Periodic Translate")
class PeriodicTranslate:
    CATEGORY = "Level & Correct"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "dx": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "dy": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "update_offsets": ("BOOLEAN", {"default": False}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'translated'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Move the data in the horizontal plane, treating it as periodic: pixels "
        "that leave one side of the image reappear on the opposite side (data "
        "wraps around). dx/dy are the move-by amounts in pixels; the data is "
        "shifted so the image content moves by (dx, dy). When update_offsets is "
        "enabled the coordinate offsets are updated the same way Gwyddion's "
        "periodic translation does, so features keep their physical positions. "
        "Equivalent to Gwyddion's ptranslate module."
    )

    KEYWORDS = ("translate", "shift", "periodic", "wrap", "roll", "move")

    def process(
        self,
        field: DataField,
        dx: int,
        dy: int,
        update_offsets: bool,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        shifted = np.roll(data, (dy % yres, dx % xres), axis=(0, 1))

        out = field.replace(data=shifted)
        if update_offsets:
            # Fold the shift exactly like ptranslate.c folds it before applying
            # the offset update.
            sx = (-dx % xres + xres) % xres
            sy = (-dy % yres + yres) % yres
            out = out.replace(
                xoff=_update_offset(field.xoff, xres, field.xreal, sx),
                yoff=_update_offset(field.yoff, yres, field.yreal, sy),
            )
        return (out,)
