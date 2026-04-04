from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Field Arithmetic")
class FieldArithmetic:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "operation": (["add", "subtract", "multiply", "divide", "min", "max", "hypot"],),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply a point-wise arithmetic operation to two DATA_FIELDs of the same resolution. "
        "add/subtract/multiply/divide/min/max perform element-wise operations; "
        "hypot computes sqrt(a² + b²) per pixel. "
    )

    KEYWORDS = ("math", "add", "subtract", "multiply", "divide", "hypot")

    def process(self, field_a: DataField, field_b: DataField, operation: str) -> tuple:
        if field_a.data.shape != field_b.data.shape:
            raise ValueError(
                f"Fields must have the same resolution: "
                f"{field_a.data.shape} vs {field_b.data.shape}"
            )

        a = field_a.data
        b = field_b.data

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            result = a / b
        elif operation == "min":
            result = np.minimum(a, b)
        elif operation == "max":
            result = np.maximum(a, b)
        elif operation == "hypot":
            result = np.hypot(a, b)
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

        return (field_a.replace(data=result),)
