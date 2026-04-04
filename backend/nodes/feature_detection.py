"""Feature detection — Canny edge and Harris corner detection."""

from __future__ import annotations

import numpy as np
from skimage.feature import canny, corner_harris, corner_peaks

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Feature Detection")
class FeatureDetection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["canny", "harris"], {"default": "canny"}),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 20.0, "step": 0.1}),
            },
            "optional": {
                "low_threshold": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "high_threshold": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01}),
                "harris_k": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.5, "step": 0.01}),
                "min_distance": ("INT", {"default": 5, "min": 1, "max": 100}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
        ('RECORD_TABLE', 'features'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect edges or corners in a surface. "
        "Canny: multi-stage edge detector with hysteresis thresholding. "
        "Harris: corner/interest point detector based on structure tensor. "
        "Outputs a feature map and a table of detected feature locations. "
        "Equivalent to Gwyddion's edge/corner detection in filters.c."
    )

    def process(
        self,
        field: DataField,
        method: str,
        sigma: float,
        low_threshold: float = 0.1,
        high_threshold: float = 0.2,
        harris_k: float = 0.05,
        min_distance: int = 5,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Normalise to [0, 1]
        dmin, dmax = data.min(), data.max()
        if dmax > dmin:
            norm = (data - dmin) / (dmax - dmin)
        else:
            norm = np.zeros_like(data)

        records: RecordTable = RecordTable()

        if method == "canny":
            edges = canny(
                norm,
                sigma=sigma,
                low_threshold=low_threshold,
                high_threshold=high_threshold,
            )
            result = edges.astype(np.float64)
            n_edge_pixels = int(edges.sum())
            edge_fraction = n_edge_pixels / data.size
            records.append({"quantity": "Edge pixels", "value": str(n_edge_pixels), "unit": ""})
            records.append({"quantity": "Edge fraction", "value": f"{edge_fraction:.4f}", "unit": ""})

        elif method == "harris":
            response = corner_harris(norm, sigma=sigma, k=harris_k)
            result = response.astype(np.float64)
            corners = corner_peaks(
                response,
                min_distance=min_distance,
                threshold_rel=0.1,
            )
            records.append({"quantity": "Corners detected", "value": str(len(corners)), "unit": ""})
            for i, (row, col) in enumerate(corners[:20]):
                x_phys = col * field.dx
                y_phys = row * field.dy
                records.append({
                    "quantity": f"Corner {i + 1}",
                    "value": f"({x_phys:.4g}, {y_phys:.4g})",
                    "unit": field.si_unit_xy,
                })

        else:
            raise ValueError(f"Unknown method: {method!r}")

        return (field.replace(data=result, si_unit_z=""), records)
