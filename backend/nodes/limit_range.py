from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Limit Range")
class LimitRange:
    """Limit a DATA_FIELD to a value range."""

    CATEGORY = "Level & Correct"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "low": ("FLOAT", {"default": 0.0, "min": -1.0e12, "max": 1.0e12, "step": 0.01}),
                "high": ("FLOAT", {"default": 1.0, "min": -1.0e12, "max": 1.0e12, "step": 0.01}),
                "mode": (["clip", "scale"], {"default": "clip"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Limit a DATA_FIELD to a given value range. Clip mode clamps every value "
        "into [min(low, high), max(low, high)]. Scale mode additionally compresses "
        "the clipped range linearly so "
        "low maps to 0 and high to 1. Physical extents and offsets are preserved."
    )

    KEYWORDS = ("clamp", "threshold", "clip", "range", "scale", "limit")

    def process(self, field: DataField, low: float, high: float, mode: str) -> tuple:
        bottom = float(min(low, high))
        top = float(max(low, high))

        clamped = np.clip(field.data, bottom, top)

        mode_name = str(mode).strip().lower()
        if mode_name == "clip":
            result = clamped
        elif mode_name == "scale":
            if not np.isfinite(bottom) or not np.isfinite(top):
                raise ValueError("low and high must be finite numbers")
            if top == bottom:
                raise ValueError(
                    "low and high must differ in scale mode "
                    "(the mapping [low, high] -> [0, 1] is degenerate)"
                )
            result = (clamped - bottom) / (top - bottom)
        else:
            raise ValueError(f"Unknown mode: {mode!r}. Choose from: clip, scale")

        return (field.replace(data=np.asarray(result, dtype=np.float64)),)
