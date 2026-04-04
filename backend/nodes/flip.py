from __future__ import annotations

from copy import deepcopy

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Flip")
class FlipField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "axis": (["x", "y"], {"default": "x"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Reflect a DATA_FIELD across the X axis (top/bottom) or Y axis (left/right). "
        "Physical extents are preserved, and stored markup overlays are mirrored with the data."
    )

    KEYWORDS = ("mirror", "reflect", "invert")

    def process(self, field: DataField, axis: str) -> tuple:
        axis_name = str(axis).strip().lower()
        if axis_name == "x":
            flipped = np.flipud(field.data).copy()
        elif axis_name == "y":
            flipped = np.fliplr(field.data).copy()
        else:
            raise ValueError(f"Unknown flip axis: {axis}")

        return (
            field.replace(
                data=np.asarray(flipped, dtype=np.float64),
                overlays=self._flip_overlays(field.overlays, axis_name),
            ),
        )

    @classmethod
    def _flip_overlays(cls, overlays: list[dict] | None, axis: str) -> list[dict]:
        if not isinstance(overlays, list):
            return []

        flipped_overlays = []
        for overlay in overlays:
            if not isinstance(overlay, dict):
                continue

            next_overlay = deepcopy(overlay)
            if str(next_overlay.get("kind", "")).strip().lower() == "markup":
                next_overlay["shapes"] = [
                    cls._flip_markup_shape(shape, axis)
                    for shape in next_overlay.get("shapes", [])
                    if isinstance(shape, dict)
                ]
            flipped_overlays.append(next_overlay)
        return flipped_overlays

    @staticmethod
    def _flip_markup_shape(shape: dict, axis: str) -> dict:
        flipped = deepcopy(shape)
        kind = str(flipped.get("kind", "")).strip().lower()

        try:
            x1 = float(flipped.get("x1"))
            y1 = float(flipped.get("y1"))
            x2 = float(flipped.get("x2"))
            y2 = float(flipped.get("y2"))
        except (TypeError, ValueError):
            return flipped

        if axis == "x":
            y1, y2 = 1.0 - y1, 1.0 - y2
        else:
            x1, x2 = 1.0 - x1, 1.0 - x2

        if kind in {"rectangle", "circle"}:
            x1, x2 = sorted((x1, x2))
            y1, y2 = sorted((y1, y2))

        flipped["x1"] = float(np.clip(x1, 0.0, 1.0))
        flipped["y1"] = float(np.clip(y1, 0.0, 1.0))
        flipped["x2"] = float(np.clip(x2, 0.0, 1.0))
        flipped["y2"] = float(np.clip(y2, 0.0, 1.0))
        return flipped
