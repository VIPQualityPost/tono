"""Extend / pad — add borders to a field with various fill methods."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Extend / Pad")
class ExtendPad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "top": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
                "bottom": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
                "left": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
                "right": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
                "method": (["mean", "edge", "mirror", "periodic", "zero"],
                           {"default": "mirror"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'padded'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Add borders to a field with configurable padding method. "
        "Mirror and periodic modes avoid edge discontinuities for FFT. "
    )

    KEYWORDS = ("border", "margin", "mirror", "periodic")

    def process(self, field: DataField, top: int, bottom: int,
                left: int, right: int, method: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        mode_map = {
            "mean": "constant",
            "edge": "edge",
            "mirror": "reflect",
            "periodic": "wrap",
            "zero": "constant",
        }
        np_mode = mode_map.get(method, "constant")

        kwargs = {}
        if method == "mean":
            kwargs["constant_values"] = data.mean()
        elif method == "zero":
            kwargs["constant_values"] = 0.0

        result = np.pad(data, ((top, bottom), (left, right)), mode=np_mode, **kwargs)

        new_xreal = result.shape[1] * field.dx
        new_yreal = result.shape[0] * field.dy
        new_xoff = field.xoff - left * field.dx
        new_yoff = field.yoff - top * field.dy

        return (field.replace(data=result, xreal=new_xreal, yreal=new_yreal,
                              xoff=new_xoff, yoff=new_yoff),)
