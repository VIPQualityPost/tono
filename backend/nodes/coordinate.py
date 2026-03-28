from __future__ import annotations
from backend.node_registry import register_node


@register_node(display_name="Coordinate")
class Coordinate:
    """Provide a fractional (x, y) point for use with Cross Section or other nodes."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    OUTPUTS = (
        ('COORD', 'point'),
    )
    FUNCTION = "process"

    DESCRIPTION = "Output a fractional (x, y) coordinate pair in [0, 1]."

    def process(self, x: float, y: float) -> tuple:
        return ((float(x), float(y)),)
