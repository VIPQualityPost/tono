from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


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

    OUTPUTS = (
        ('DATA_FIELD', 'edges'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect edges using Sobel, Prewitt, Laplacian, or LoG operators. "
    )

    KEYWORDS = ("sobel", "prewitt", "laplacian", "log", "gradient", "edges")

    def process(self, field: DataField, method: str, sigma: float) -> tuple:
        from scipy.ndimage import sobel, prewitt, gaussian_laplace, laplace
        data = field.data

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
