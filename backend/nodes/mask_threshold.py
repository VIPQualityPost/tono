from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_preview, emit_overlay
from backend.data_types import DataField, encode_preview, RecordTable
from backend.nodes.helpers import _mask_overlay


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
        ('RECORD_TABLE', 'threshold'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a binary mask by thresholding data. "
        "Otsu automatically finds the optimal threshold. "
        "Equivalent to Gwyddion's threshold and otsu_threshold modules."
    )

    _broadcast_fn = None
    _current_node_id: str = ""

    def process(self, field: DataField, method: str, threshold: float, direction: str) -> tuple:
        data = field.data

        raw_counts, bin_edges = np.histogram(data.ravel(), bins=256)
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        counts = raw_counts.astype(np.float64)
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
            mask = (data >= t).astype(np.uint8) * 255
        else:
            mask = (data < t).astype(np.uint8) * 255

        emit_preview(encode_preview(_mask_overlay(field, mask)))

        table = RecordTable([
            {"quantity": "threshold", "value": threshold, "unit": field.si_unit_xy},
        ])
        
        return (mask, table)
