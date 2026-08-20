from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.nodes.helpers import mask_to_bool, bool_to_mask, emit_mask_preview


_MASK_BOOLEAN_OPERATIONS = {
    "and": lambda a, b: a & b,
    "or": lambda a, b: a | b,
    "xor": lambda a, b: a ^ b,
    "xnor": lambda a, b: ~(a ^ b),
    "nand": lambda a, b: ~(a & b),
    "nor": lambda a, b: ~(a | b),
    "a_minus_b": lambda a, b: a & ~b,
    "b_minus_a": lambda a, b: b & ~a,
    "a": lambda a, b: a,
    "b": lambda a, b: b,
    "not_a": lambda a, b: ~a,
    "not_b": lambda a, b: ~b,
    "a_implies_b": lambda a, b: ~a | b,
    "b_implies_a": lambda a, b: ~b | a,
    "false": lambda a, b: np.zeros_like(a, dtype=bool),
    "true": lambda a, b: np.ones_like(a, dtype=bool),
}


@register_node(display_name="Mask Operations")
class MaskOperations:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask_a": ("IMAGE",),
                "mask_b": ("IMAGE",),
                "operation": (list(_MASK_BOOLEAN_OPERATIONS.keys()),),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Apply boolean logic to two binary masks. Includes AND, OR, XOR, NAND, NOR, "
        "XNOR, directional subtraction, implication, pass-through, and constant true/false outputs."
    )

    KEYWORDS = ("boolean", "and", "or", "xor", "logic", "union", "intersect", "subtract")

    def process(
        self,
        mask_a: np.ndarray,
        mask_b: np.ndarray,
        operation: str,
    ) -> tuple:
        a = mask_to_bool(mask_a)
        b = mask_to_bool(mask_b)

        op = _MASK_BOOLEAN_OPERATIONS.get(operation)
        if op is None:
            raise ValueError(f"Unknown mask operation: {operation}")
        result = op(a, b)

        out = bool_to_mask(result)

        emit_mask_preview(None, out)

        return (out,)
