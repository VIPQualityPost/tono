from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Fix Zero")
class FixZero:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["min", "mean", "median"],),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'zeroed'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Shift data so that the minimum (or mean/median) is zero. "
    )

    KEYWORDS = ("offset", "subtract", "baseline", "datum")

    def process(self, field: DataField, method: str) -> tuple:
        data = field.data.copy()
        if method == "min":
            data -= data.min()
        elif method == "mean":
            data -= data.mean()
        elif method == "median":
            data -= np.median(data)
        else:
            raise ValueError(f"Unknown method: {method}")
        return (field.replace(data=data),)
