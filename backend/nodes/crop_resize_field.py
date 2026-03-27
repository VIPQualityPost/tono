from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, datafield_to_uint8, encode_preview


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

        emit_overlay({
            "kind": "crop_box",
            "image": encode_preview(datafield_to_uint8(field, field.colormap)),
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "a_locked": corner_a is not None,
            "b_locked": corner_b is not None,
        })

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
            overlays=[],
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
