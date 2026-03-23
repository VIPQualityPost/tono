"""
Grain/feature detection nodes.

Gwyddion equivalents:
  ThresholdMask → threshold.c / otsu_threshold.c
  GrainAnalysis → gwy_data_field_grains_get_values (grains-values.c)
"""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


# ---------------------------------------------------------------------------
# ThresholdMask
# ---------------------------------------------------------------------------

@register_node(display_name="Threshold Mask")
class ThresholdMask:
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
    CATEGORY = "grains"
    DESCRIPTION = (
        "Create a binary mask by thresholding data. "
        "Otsu automatically finds the optimal threshold. "
        "Equivalent to Gwyddion's threshold and otsu_threshold modules."
    )

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

        return (mask,)


# ---------------------------------------------------------------------------
# GrainAnalysis
# ---------------------------------------------------------------------------

@register_node(display_name="Grain Analysis")
class GrainAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    RETURN_TYPES = ("TABLE",)
    RETURN_NAMES = ("grain_stats",)
    FUNCTION = "process"
    CATEGORY = "grains"
    DESCRIPTION = (
        "Label connected grain regions in a binary mask and compute per-grain statistics: "
        "area, equivalent diameter, mean/max height, bounding box. "
        "Equivalent to gwy_data_field_grains_get_values."
    )

    def process(self, field: DataField, mask: np.ndarray, min_size: int) -> tuple:
        from scipy.ndimage import label, find_objects

        binary = (mask > 127).astype(np.int32)
        labeled, n_grains = label(binary)

        pixel_area = field.dx * field.dy  # m^2 per pixel

        rows = []
        for grain_id in range(1, n_grains + 1):
            grain_pixels = labeled == grain_id
            area_px = int(grain_pixels.sum())
            if area_px < min_size:
                continue

            area_m2 = area_px * pixel_area
            equiv_diam = float(2.0 * np.sqrt(area_m2 / np.pi))

            heights = field.data[grain_pixels]
            mean_h = float(heights.mean())
            max_h = float(heights.max())

            # Bounding box
            ys, xs = np.where(grain_pixels)
            bbox = f"({int(xs.min())},{int(ys.min())})-({int(xs.max())},{int(ys.max())})"

            rows.append({
                "grain_id":     grain_id,
                "area_px":      area_px,
                "area_m2":      area_m2,
                "equiv_diam_m": equiv_diam,
                "mean_height":  mean_h,
                "max_height":   max_h,
                "bbox":         bbox,
            })

        return (rows,)
