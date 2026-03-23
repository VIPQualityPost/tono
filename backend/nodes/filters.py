"""
Filter nodes — Gwyddion-equivalent image filters.

Gwyddion equivalents:
  GaussianFilter  → gwy_data_field_filter_gaussian
  MedianFilter    → gwy_data_field_filter_median
  EdgeDetect      → gwy_data_field_filter_sobel / laplacian / log
"""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


# ---------------------------------------------------------------------------
# GaussianFilter
# ---------------------------------------------------------------------------

@register_node(display_name="Gaussian Filter")
class GaussianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 50.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = "Apply a Gaussian blur. Equivalent to gwy_data_field_filter_gaussian."

    def process(self, field: DataField, sigma: float) -> tuple:
        from scipy.ndimage import gaussian_filter
        data = gaussian_filter(field.data.copy(), sigma=float(sigma))
        return (field.replace(data=data),)


# ---------------------------------------------------------------------------
# MedianFilter
# ---------------------------------------------------------------------------

@register_node(display_name="Median Filter")
class MedianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "size": ("INT", {"default": 3, "min": 1, "max": 21, "step": 2}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = "Apply a median filter. Equivalent to gwy_data_field_filter_median."

    def process(self, field: DataField, size: int) -> tuple:
        from scipy.ndimage import median_filter
        size = max(1, int(size))
        data = median_filter(field.data.copy(), size=size)
        return (field.replace(data=data),)


# ---------------------------------------------------------------------------
# EdgeDetect
# ---------------------------------------------------------------------------

@register_node(display_name="Edge Detect")
class EdgeDetect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["sobel", "prewitt", "laplacian", "log"],),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("edges",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = (
        "Detect edges using Sobel, Prewitt, Laplacian, or LoG operators. "
        "Equivalent to gwy_data_field_filter_sobel / gwy_data_field_filter_laplacian."
    )

    def process(self, field: DataField, method: str, sigma: float) -> tuple:
        from scipy.ndimage import sobel, prewitt, gaussian_laplace, laplace
        data = field.data.copy()

        if method == "sobel":
            sx = sobel(data, axis=1)
            sy = sobel(data, axis=0)
            result = np.hypot(sx, sy)
        elif method == "prewitt":
            px = prewitt(data, axis=1)
            py = prewitt(data, axis=0)
            result = np.hypot(px, py)
        elif method == "laplacian":
            result = laplace(data)
        elif method == "log":
            result = gaussian_laplace(data, sigma=float(sigma))
        else:
            raise ValueError(f"Unknown edge detection method: {method}")

        return (field.replace(data=result),)
