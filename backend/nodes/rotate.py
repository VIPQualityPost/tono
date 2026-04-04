from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_warning
from backend.data_types import DataField


@register_node(display_name="Rotate")
class RotateField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "angle": ("FLOAT", {"default": 90.0, "min": -360.0, "max": 360.0, "step": 1.0}),
                "interpolation": (["bilinear", "nearest", "bicubic"],),
                "expand_canvas": ("BOOLEAN", {"default": True}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Rotate a DATA_FIELD counterclockwise by an angle in degrees. "
        "Optionally expand the canvas to keep the full rotated field while preserving the field center."
    )

    KEYWORDS = ("turn", "angle", "spin", "orient")

    def process(
        self,
        field: DataField,
        angle: float,
        interpolation: str,
        expand_canvas: bool,
    ) -> tuple:
        if field.overlays:
            emit_warning("Rotate clears annotation/markup overlays!")

        angle = float(angle)
        order_map = {
            "nearest": 0,
            "bilinear": 1,
            "bicubic": 3,
        }
        if interpolation not in order_map:
            raise ValueError(f"Unknown interpolation mode: {interpolation}")

        normalized_angle = angle % 360.0
        snapped_quarters = int(round(normalized_angle / 90.0)) % 4
        snapped_angle = snapped_quarters * 90.0
        is_right_angle = abs(normalized_angle - snapped_angle) < 1e-9

        if is_right_angle and expand_canvas:
            rotated = np.rot90(field.data, k=snapped_quarters).copy()
        elif abs(normalized_angle) < 1e-9:
            rotated = field.data.copy()
        else:
            from scipy.ndimage import rotate as nd_rotate

            rotated = nd_rotate(
                field.data,
                angle=angle,
                reshape=bool(expand_canvas),
                order=order_map[interpolation],
                mode="nearest",
                prefilter=order_map[interpolation] > 1,
            )

        new_xreal, new_yreal = self._rotated_extents(field, angle, expand_canvas)
        center_x = field.xoff + field.xreal / 2.0
        center_y = field.yoff + field.yreal / 2.0

        result = field.replace(
            data=np.asarray(rotated, dtype=np.float64),
            xreal=new_xreal,
            yreal=new_yreal,
            xoff=center_x - new_xreal / 2.0,
            yoff=center_y - new_yreal / 2.0,
            overlays=[],
        )
        return (result,)

    @staticmethod
    def _rotated_extents(field: DataField, angle: float, expand_canvas: bool) -> tuple[float, float]:
        if not expand_canvas:
            return (field.xreal, field.yreal)

        theta = np.deg2rad(angle)
        cos_t = abs(float(np.cos(theta)))
        sin_t = abs(float(np.sin(theta)))
        new_xreal = field.xreal * cos_t + field.yreal * sin_t
        new_yreal = field.xreal * sin_t + field.yreal * cos_t
        return (new_xreal, new_yreal)
