from __future__ import annotations
from backend.node_registry import register_node


@register_node(display_name="Number")
class Number:
    """Provide a fixed scalar value that can feed FLOAT or INT widget sockets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {"default": 0.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Output a fixed numeric value. "
        "When connected to FLOAT inputs the exact value is used; "
        "INT inputs round to the nearest integer at execution time."
    )

    def process(self, value: float) -> tuple:
        return (float(value),)
