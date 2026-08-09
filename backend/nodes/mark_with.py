from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask, emit_mask_preview


# Point-wise condition for each operation.  Relational operations produce the
# binary comparison result directly; arithmetic operations follow the
# mask-arithmetic convention of Gwyddion's mark_with.c (a value map becomes a
# mask by marking non-zero samples).
_MARK_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "+": lambda a, b: (a + b) != 0,
    "-": lambda a, b: (a - b) != 0,
    "*": lambda a, b: (a * b) != 0,
    "/": lambda a, b: np.divide(a, b) != 0,
    "min": lambda a, b: np.minimum(a, b) != 0,
    "max": lambda a, b: np.maximum(a, b) != 0,
}


@register_node(display_name="Mark With")
class MarkWith:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "operation": (list(_MARK_OPS.keys()),),
                "invert_mask": ("BOOLEAN", {"default": False}),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    CATEGORY = "Mask"

    DESCRIPTION = (
        "Create a binary mask from the point-wise comparison of two data fields. "
        "Relational operations (==, !=, <, <=, >, >=) mark pixels where the condition "
        "between field_a and field_b holds; arithmetic operations mark pixels where the "
        "combined value is non-zero. Optionally invert the resulting mask."
    )

    KEYWORDS = ("mask", "compare", "relational", "mark", "condition", "select")

    def process(
        self,
        field_a: DataField,
        field_b: DataField,
        operation: str,
        invert_mask: bool,
    ) -> tuple:
        if field_a.data.shape != field_b.data.shape:
            raise ValueError(
                f"Fields must have the same resolution: "
                f"{field_a.data.shape} vs {field_b.data.shape}"
            )

        op = _MARK_OPS.get(operation)
        if op is None:
            raise ValueError(f"Unknown operation: {operation!r}")

        with np.errstate(divide="ignore", invalid="ignore"):
            condition = op(field_a.data, field_b.data)

        if invert_mask:
            condition = ~condition

        out = bool_to_mask(condition)

        emit_mask_preview(field_a, out)

        return (out,)
