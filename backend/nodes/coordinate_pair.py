from __future__ import annotations
from backend.node_registry import register_node


@register_node(display_name="Coordinate Pair")
class CoordinatePair:
    """Provide a pair of Coordinates, for drawing lines between markers, etc."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("COORD",),
                "b": ("COORD",),
            }
        }

    RETURN_TYPES = ("COORDPAIR",)
    RETURN_NAMES = ("coord pair",)
    FUNCTION = "process"

    DESCRIPTION = "Output a pair of coordinates."

    def process(self, a: tuple, b: tuple) -> tuple:
        return ((a, b),)
