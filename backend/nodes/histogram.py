from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import frac_to_index, histogram_with_centers


@register_node(display_name="Histogram")
class Histogram:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_bins": ("INT", {"default": 256, "min": 10, "max": 1000, "step": 1}),
                "y_scale": (["linear", "log"],),
                "x1": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            }
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'measurements'),
        ('COORDPAIR', 'marker_pair'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the height distribution histogram (DH). "
        "Use log scale to reveal small peaks next to a dominant background. "
        "Outputs marker measurements while showing the histogram interactively in-node. "
    )

    def process(
        self,
        field: DataField,
        n_bins: int,
        y_scale: str = "linear",
        x1: float = 0.25,
        y1: float = 0.5,
        x2: float = 0.75,
        y2: float = 0.5,
    ) -> tuple:
        counts, bin_centers = histogram_with_centers(field.data, n_bins)
        if y_scale == "log":
            counts = np.log10(1.0 + counts)

        x1 = float(np.clip(x1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 0.0 + 1.0))

        xmin = float(np.min(bin_centers)) if len(bin_centers) else 0.0
        xmax = float(np.max(bin_centers)) if len(bin_centers) else 1.0

        idx_a = frac_to_index(bin_centers, x1)
        idx_b = frac_to_index(bin_centers, x2)
        xa = float(bin_centers[idx_a]) if len(bin_centers) else 0.0
        xb = float(bin_centers[idx_b]) if len(bin_centers) else 0.0
        ya = float(counts[idx_a]) if len(counts) else 0.0
        yb = float(counts[idx_b]) if len(counts) else 0.0
        count_unit = "count" if y_scale == "linear" else "log10(1+count)"

        emit_overlay({
            "kind": "line_plot",
            "section_title": "Histogram",
            "line": counts.tolist(),
            "x_axis": bin_centers.astype(np.float64).tolist(),
            "x_unit": field.si_unit_z,
            "x1": float(np.clip(x1, 0.0, 1.0)),
            "x2": float(np.clip(x2, 0.0, 1.0)),
            "y1": float(y1),
            "y2": float(y2),
            "a_locked": False,
            "b_locked": False,
        })

        table = RecordTable([
            {"quantity": "delta X",    "value": xb - xa, "unit": field.si_unit_z},
            {"quantity": "delta Y",    "value": yb - ya, "unit": count_unit},
            {"quantity": "A position", "value": xa, "unit": field.si_unit_z},
            {"quantity": "A count",    "value": ya, "unit": count_unit},
            {"quantity": "B position", "value": xb, "unit": field.si_unit_z},
            {"quantity": "B count",    "value": yb, "unit": count_unit},
        ])
        return (table, ((x1, y1), (x2, y2)))
