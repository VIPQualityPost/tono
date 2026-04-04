from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import bool_to_mask, histogram_with_centers, emit_mask_preview


@register_node(display_name="Threshold Mask")
class ThresholdMask:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["absolute", "relative", "otsu"],),
                "threshold": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001, "socket_only": True}),
                "direction": (["above", "below"],),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
        ('FLOAT', 'threshold'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a binary mask by thresholding data. "
        "Otsu automatically finds the optimal threshold. "
    )

    KEYWORDS = ("otsu", "binarize", "segment", "cutoff", "level")

    def process(self, field: DataField, method: str, threshold: float, direction: str) -> tuple:
        data = field.data

        counts, bin_centers = histogram_with_centers(data)
        xmin = float(bin_centers[0]) if len(bin_centers) else 0.0
        xmax = float(bin_centers[-1]) if len(bin_centers) else 1.0

        if method == "otsu":
            from skimage.filters import threshold_otsu
            t = threshold_otsu(data)
        elif method == "absolute":
            t = float(threshold)
        elif method == "relative":
            dmin, dmax = data.min(), data.max()
            t = dmin + float(threshold) * (dmax - dmin)
        else:
            raise ValueError(f"Unknown threshold method: {method}")

        span = xmax - xmin if xmax != xmin else 1.0
        threshold_frac = float(np.clip((t - xmin) / span, 0.0, 1.0))

        emit_overlay({
            "kind": "threshold_histogram",
            "section_title": "Histogram",
            "line": counts.tolist(),
            "x_axis": bin_centers.tolist(),
            "x_unit": field.si_unit_z,
            "threshold_frac": threshold_frac,
            "x_min": xmin,
            "x_max": xmax,
            "method": method,
            "locked": method == "otsu",
        })

        if direction == "above":
            mask = bool_to_mask(data >= t)
        else:
            mask = bool_to_mask(data < t)

        emit_mask_preview(field, mask)

        table = RecordTable([
            {"quantity": "threshold", "value": threshold, "unit": field.si_unit_xy},
        ])
        
        return (mask, table)
