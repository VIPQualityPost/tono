"""
Mask operation nodes — creation, morphology, and boolean combination.

Gwyddion equivalents:
  ThresholdMask  → threshold.c / otsu_threshold.c
  MaskMorphology → mask_morph.c (erode, dilate, open, close)
  MaskInvert     → (bitwise NOT on mask)
  MaskCombine    → (boolean ops between two masks)
"""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, encode_preview


def _mask_overlay(field: DataField, mask: np.ndarray) -> np.ndarray:
    """Render greyscale base image with red shadow on masked (255) pixels.

    Returns (H, W, 3) uint8 array.
    """
    grey = datafield_to_uint8(field, "gray")  # (H, W, 3) uint8
    overlay = grey.astype(np.float64)
    mask_bool = mask == 255
    alpha = 0.45
    overlay[mask_bool, 0] = overlay[mask_bool, 0] * (1 - alpha) + 255 * alpha
    overlay[mask_bool, 1] = overlay[mask_bool, 1] * (1 - alpha)
    overlay[mask_bool, 2] = overlay[mask_bool, 2] * (1 - alpha)
    return np.clip(overlay, 0, 255).astype(np.uint8)


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
        from scipy.ndimage import binary_dilation, binary_erosion

        binary = mask > 127

        if shape == "disk":
            y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
            struct = (x * x + y * y) <= radius * radius
        else:
            size = 2 * radius + 1
            struct = np.ones((size, size), dtype=bool)

        if operation == "dilate":
            result = binary_dilation(binary, structure=struct)
        elif operation == "erode":
            result = binary_erosion(binary, structure=struct)
        elif operation == "open":
            result = binary_dilation(
                binary_erosion(binary, structure=struct),
                structure=struct,
            )
        elif operation == "close":
            result = binary_erosion(
                binary_dilation(binary, structure=struct),
                structure=struct,
            )
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
