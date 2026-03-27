from __future__ import annotations
import numpy as np
from backend.node_registry import register_node


@register_node(display_name="Float Slider")
class RangeSlider:
    """Interactive float control node with min/max bounds and a slider value."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {"default": 0.0, "step": 0.01}),
                "max_value": ("FLOAT", {"default": 1.0, "step": 0.01}),
                "value": ("FLOAT", {
                    "default": 0.5,
                    "step": 0.01,
                    "slider": True,
                    "min_widget": "min_value",
                    "max_widget": "max_value",
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Interactive float slider. Set min and max bounds, then drag the slider to output a FLOAT value."
    )

    def process(self, min_value: float, max_value: float, value: float) -> tuple:
        lo = min(float(min_value), float(max_value))
        hi = max(float(min_value), float(max_value))
        if hi == lo:
            return (lo,)
        return (float(np.clip(float(value), lo, hi)),)
