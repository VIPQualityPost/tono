from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Resample")
class Resample:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "width": ("INT", {"default": 256, "min": 2, "max": 16384, "step": 1}),
                "height": ("INT", {"default": 256, "min": 2, "max": 16384, "step": 1}),
                "interpolation": (["linear", "cubic", "nearest"], {"default": "linear"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'resampled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Resample a DATA_FIELD to a new pixel resolution while preserving physical dimensions. "
        "Physical size (xreal, yreal) is unchanged; pixel size dx/dy scales accordingly. "
    )

    KEYWORDS = ("resize", "rescale", "interpolate", "bilinear", "bicubic", "nearest", "zoom")

    _ORDERS = {"nearest": 0, "linear": 1, "cubic": 3}

    def process(self, field: DataField, width: int, height: int, interpolation: str) -> tuple:
        from scipy.ndimage import zoom

        if interpolation not in self._ORDERS:
            raise ValueError(
                f"Unknown interpolation {interpolation!r}. "
                f"Choose from: {list(self._ORDERS)}"
            )

        old_yres, old_xres = field.data.shape
        zy = height / old_yres
        zx = width / old_xres

        result = zoom(field.data, (zy, zx), order=self._ORDERS[interpolation])

        # Physical dimensions stay the same; xres/yres are re-derived from data.shape.
        return (field.replace(data=result, xreal=field.xreal, yreal=field.yreal),)
