"""
Mask operation nodes — creation, morphology, and boolean combination.

Gwyddion equivalents:
  ThresholdMask  → threshold.c / otsu_threshold.c
  MaskMorphology → mask_morph.c (erode, dilate, open, close)
  MaskInvert     → (bitwise NOT on mask)
  MaskCombine    → (boolean ops between two masks)
"""

from __future__ import annotations
from functools import lru_cache
import json
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, encode_preview


def _mask_overlay(field: DataField, mask: np.ndarray) -> np.ndarray:
    """Render greyscale base image with red shadow on masked (255) pixels.

    Returns (H, W, 3) uint8 array.
    """
    grey = datafield_to_uint8(field, "gray")  # (H, W, 3) uint8
    mask_bool = mask > 127
    if not np.any(mask_bool):
        return grey

    overlay = grey.copy()
    red = overlay[..., 0]
    green = overlay[..., 1]
    blue = overlay[..., 2]

    # Integer alpha blend equivalent to a 45% red overlay, without float64 work.
    red_vals = red[mask_bool].astype(np.uint16)
    green_vals = green[mask_bool].astype(np.uint16)
    blue_vals = blue[mask_bool].astype(np.uint16)
    red[mask_bool] = ((red_vals * 55) + (255 * 45) + 50) // 100
    green[mask_bool] = ((green_vals * 55) + 50) // 100
    blue[mask_bool] = ((blue_vals * 55) + 50) // 100
    return overlay


@lru_cache(maxsize=128)
def _mask_structure(radius: int, shape: str) -> np.ndarray:
    radius = max(1, int(radius))
    if shape == "disk":
        y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
        struct = (x * x + y * y) <= radius * radius
    else:
        size = 2 * radius + 1
        struct = np.ones((size, size), dtype=bool)
    struct.setflags(write=False)
    return struct


def _clamp_fraction(value) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _parse_mask_strokes(mask_paths) -> list[dict]:
    if isinstance(mask_paths, list):
        raw_strokes = mask_paths
    elif isinstance(mask_paths, str) and mask_paths.strip():
        try:
            parsed = json.loads(mask_paths)
        except json.JSONDecodeError:
            return []
        raw_strokes = parsed if isinstance(parsed, list) else []
    else:
        return []

    strokes = []
    for stroke in raw_strokes:
        if not isinstance(stroke, dict):
            continue
        raw_points = stroke.get("points")
        if not isinstance(raw_points, list):
            continue

        points = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            if "x" not in point or "y" not in point:
                continue
            points.append({
                "x": _clamp_fraction(point.get("x")),
                "y": _clamp_fraction(point.get("y")),
            })

        if not points:
            continue

        try:
            size = max(1, int(round(float(stroke.get("size", 1)))))
        except (TypeError, ValueError):
            size = 1

        strokes.append({
            "size": size,
            "points": points,
        })

    return strokes


def _rasterize_mask(width: int, height: int, strokes: list[dict], default_pen_size: int) -> np.ndarray:
    from PIL import Image, ImageDraw

    width = max(1, int(width))
    height = max(1, int(height))
    default_pen_size = max(1, int(default_pen_size))

    mask_image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_image)

    for stroke in strokes:
        points = stroke.get("points") or []
        if not points:
            continue

        size = stroke.get("size", default_pen_size)
        try:
            size = max(1, int(round(float(size))))
        except (TypeError, ValueError):
            size = default_pen_size

        pixel_points = []
        for point in points:
            px = int(round(_clamp_fraction(point.get("x")) * (width - 1)))
            py = int(round(_clamp_fraction(point.get("y")) * (height - 1)))
            pixel_points.append((px, py))

        radius = max(0.5, size / 2.0)

        if len(pixel_points) == 1:
            x, y = pixel_points[0]
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
            continue

        draw.line(pixel_points, fill=255, width=size)
        for x, y in pixel_points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)

    return np.asarray(mask_image, dtype=np.uint8)


# ---------------------------------------------------------------------------
# DrawMask
# ---------------------------------------------------------------------------

@register_node(display_name="Draw Mask")
class DrawMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "pen_size": ("INT", {"default": 12, "min": 1, "max": 128, "step": 1}),
                "invert": ("BOOLEAN", {"default": False}),
                "clear_mask": ("BUTTON", {"label": "Clear Mask", "set_widgets": {"mask_paths": "[]"}}),
                "mask_paths": ("STRING", {"default": "[]", "hidden": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "mask"
    DESCRIPTION = (
        "Paint a binary mask directly over an image preview. "
        "Pen size controls newly drawn strokes, the overlay lets you clear the mask, "
        "and invert flips the final binary output."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(self, field: DataField, pen_size: int, invert: bool, mask_paths: str) -> tuple:
        strokes = _parse_mask_strokes(mask_paths)
        mask = _rasterize_mask(field.xres, field.yres, strokes, pen_size)
        if invert:
            mask = np.where(mask > 127, np.uint8(0), np.uint8(255))

        if DrawMask._broadcast_overlay_fn is not None:
            DrawMask._broadcast_overlay_fn(
                DrawMask._current_node_id,
                {
                    "kind": "mask_paint",
                    "section_title": "Mask",
                    "image": encode_preview(datafield_to_uint8(field, "gray")),
                    "image_width": field.xres,
                    "image_height": field.yres,
                    "invert": bool(invert),
                },
            )

        return (mask,)


# ---------------------------------------------------------------------------
# ThresholdMask
# ---------------------------------------------------------------------------

@register_node(display_name="Threshold Mask")
class ThresholdMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["otsu", "absolute", "relative"],),
                "threshold": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "direction": (["above", "below"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "mask"
    DESCRIPTION = (
        "Create a binary mask by thresholding data. "
        "Otsu automatically finds the optimal threshold. "
        "Equivalent to Gwyddion's threshold and otsu_threshold modules."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, field: DataField, method: str, threshold: float, direction: str) -> tuple:
        data = field.data

        if method == "otsu":
            from skimage.filters import threshold_otsu
            t = threshold_otsu(data)
        elif method == "absolute":
            t = float(threshold)
        elif method == "relative":
            # threshold is a fraction [0, 1] of the data range
            dmin, dmax = data.min(), data.max()
            t = dmin + float(threshold) * (dmax - dmin)
        else:
            raise ValueError(f"Unknown threshold method: {method}")

        if direction == "above":
            mask = (data >= t).astype(np.uint8) * 255
        else:
            mask = (data < t).astype(np.uint8) * 255

        if ThresholdMask._broadcast_fn is not None:
            overlay = _mask_overlay(field, mask)
            ThresholdMask._broadcast_fn(
                ThresholdMask._current_node_id, encode_preview(overlay),
            )

        return (mask,)


# ---------------------------------------------------------------------------
# MaskMorphology
# ---------------------------------------------------------------------------

@register_node(display_name="Mask Morphology")
class MaskMorphology:
    """Morphological operations on binary masks.

    Equivalent to Gwyddion's mask_morph.c (erode, dilate, open, close).
    """
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "operation": (["dilate", "erode", "open", "close"],),
                "radius": ("INT", {"default": 1, "min": 1, "max": 50, "step": 1}),
                "shape": (["disk", "square"],),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "mask"
    DESCRIPTION = (
        "Apply morphological operations to a binary mask. "
        "Dilate expands regions, erode shrinks them, "
        "open (erode then dilate) removes small spots, "
        "close (dilate then erode) fills small holes. "
        "Equivalent to Gwyddion mask_morph."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, mask: np.ndarray, operation: str, radius: int, shape: str,
                field: DataField | None = None) -> tuple:
        from scipy.ndimage import binary_closing, binary_dilation, binary_erosion, binary_opening

        binary = mask > 127
        struct = _mask_structure(radius, shape)

        if operation == "dilate":
            result = binary_dilation(binary, structure=struct)
        elif operation == "erode":
            result = binary_erosion(binary, structure=struct)
        elif operation == "open":
            result = binary_opening(binary, structure=struct)
        elif operation == "close":
            result = binary_closing(binary, structure=struct)
        else:
            raise ValueError(f"Unknown morphological operation: {operation}")

        out = result.astype(np.uint8) * 255

        if field is not None and MaskMorphology._broadcast_fn is not None:
            overlay = _mask_overlay(field, out)
            MaskMorphology._broadcast_fn(
                MaskMorphology._current_node_id, encode_preview(overlay),
            )

        return (out,)


# ---------------------------------------------------------------------------
# MaskInvert
# ---------------------------------------------------------------------------

@register_node(display_name="Mask Invert")
class MaskInvert:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "mask"
    DESCRIPTION = "Invert a binary mask — swap masked and unmasked regions."

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, mask: np.ndarray, field: DataField | None = None) -> tuple:
        out = np.where(mask > 127, np.uint8(0), np.uint8(255))

        if field is not None and MaskInvert._broadcast_fn is not None:
            overlay = _mask_overlay(field, out)
            MaskInvert._broadcast_fn(
                MaskInvert._current_node_id, encode_preview(overlay),
            )

        return (out,)


# ---------------------------------------------------------------------------
# MaskCombine
# ---------------------------------------------------------------------------

@register_node(display_name="Mask Combine")
class MaskCombine:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask_a": ("IMAGE",),
                "mask_b": ("IMAGE",),
                "operation": (["and", "or", "xor", "subtract"],),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "process"
    CATEGORY = "mask"
    DESCRIPTION = (
        "Combine two binary masks with a boolean operation. "
        "AND keeps overlap, OR merges, XOR keeps non-overlapping regions, "
        "subtract removes mask_b from mask_a."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, mask_a: np.ndarray, mask_b: np.ndarray, operation: str,
                field: DataField | None = None) -> tuple:
        a = mask_a > 127
        b = mask_b > 127

        if operation == "and":
            result = a & b
        elif operation == "or":
            result = a | b
        elif operation == "xor":
            result = a ^ b
        elif operation == "subtract":
            result = a & ~b
        else:
            raise ValueError(f"Unknown mask operation: {operation}")

        out = result.astype(np.uint8) * 255

        if field is not None and MaskCombine._broadcast_fn is not None:
            overlay = _mask_overlay(field, out)
            MaskCombine._broadcast_fn(
                MaskCombine._current_node_id, encode_preview(overlay),
            )

        return (out,)
