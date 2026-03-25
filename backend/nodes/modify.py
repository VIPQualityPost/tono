"""
Modify nodes — geometric transforms for DATA_FIELDs.
"""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, encode_preview


# ---------------------------------------------------------------------------
# CropResizeField
# ---------------------------------------------------------------------------

@register_node(display_name="Crop / Resize")
class CropResizeField:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "x1": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "target_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1}),
                "target_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1}),
                "interpolation": (["bilinear", "nearest", "bicubic"],),
            },
            "optional": {
                "corner_a": ("COORD",),
                "corner_b": ("COORD",),
            },
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "process"
    CATEGORY = "modify"
    DESCRIPTION = (
        "Crop a DATA_FIELD with a draggable rectangle defined by two corners, then optionally resize it. "
        "Incoming COORD inputs can lock either corner. Cropping updates physical extents and offsets; "
        "resizing preserves the cropped physical size."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self,
        field: DataField,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        target_width: int,
        target_height: int,
        interpolation: str,
        corner_a=None,
        corner_b=None,
    ) -> tuple:
        if corner_a is not None:
            x1, y1 = float(corner_a[0]), float(corner_a[1])
        if corner_b is not None:
            x2, y2 = float(corner_b[0]), float(corner_b[1])

        x1 = float(np.clip(x1, 0.0, 1.0))
        y1 = float(np.clip(y1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 1.0))
        y2 = float(np.clip(y2, 0.0, 1.0))

        if CropResizeField._broadcast_overlay_fn is not None:
            CropResizeField._broadcast_overlay_fn(
                CropResizeField._current_node_id,
                {
                    "kind": "crop_box",
                    "image": encode_preview(datafield_to_uint8(field, field.colormap)),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "a_locked": corner_a is not None,
                    "b_locked": corner_b is not None,
                },
            )

        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        if right <= left or bottom <= top:
            raise ValueError("Crop region must have non-zero width and height.")

        px0 = int(np.floor(left * field.xres))
        py0 = int(np.floor(top * field.yres))
        px1 = int(np.ceil(right * field.xres))
        py1 = int(np.ceil(bottom * field.yres))

        px0 = min(max(px0, 0), field.xres - 1)
        py0 = min(max(py0, 0), field.yres - 1)
        px1 = min(max(px1, px0 + 1), field.xres)
        py1 = min(max(py1, py0 + 1), field.yres)

        cropped = field.data[py0:py1, px0:px1].copy()
        cropped_field = field.replace(
            data=cropped,
            xreal=(px1 - px0) * field.dx,
            yreal=(py1 - py0) * field.dy,
            xoff=field.xoff + px0 * field.dx,
            yoff=field.yoff + py0 * field.dy,
        )

        target_width, target_height = self._resolve_target_shape(
            cropped_field.xres, cropped_field.yres, target_width, target_height,
        )
        if (target_width, target_height) == (cropped_field.xres, cropped_field.yres):
            return (cropped_field,)

        from PIL import Image

        resample_map = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
        }
        if interpolation not in resample_map:
            raise ValueError(f"Unknown interpolation mode: {interpolation}")

        resized = Image.fromarray(cropped_field.data.astype(np.float32)).resize(
            (target_width, target_height),
            resample=resample_map[interpolation],
        )
        resized_data = np.asarray(resized, dtype=np.float64)
        return (cropped_field.replace(data=resized_data),)

    @staticmethod
    def _resolve_target_shape(
        width: int,
        height: int,
        target_width: int,
        target_height: int,
    ) -> tuple[int, int]:
        target_width = int(target_width)
        target_height = int(target_height)

        if target_width < 0 or target_height < 0:
            raise ValueError("Target dimensions must be zero or positive.")

        if target_width == 0 and target_height == 0:
            return (width, height)
        if target_width == 0:
            target_width = max(1, int(round(width * (target_height / height))))
        if target_height == 0:
            target_height = max(1, int(round(height * (target_width / width))))

        return (max(1, target_width), max(1, target_height))


# ---------------------------------------------------------------------------
# RotateField
# ---------------------------------------------------------------------------

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

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "process"
    CATEGORY = "modify"
    DESCRIPTION = (
        "Rotate a DATA_FIELD counterclockwise by an angle in degrees. "
        "Optionally expand the canvas to keep the full rotated field while preserving the field center."
    )

    def process(
        self,
        field: DataField,
        angle: float,
        interpolation: str,
        expand_canvas: bool,
    ) -> tuple:
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
