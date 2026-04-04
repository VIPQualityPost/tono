from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="Entropy")
class Entropy:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mode": (["height values", "slope magnitude"], {"default": "height values"}),
                "n_bins": ("INT", {"default": 256, "min": 16, "max": 1024}),
            }
        }

    OUTPUTS = (
        ('FLOAT', 'entropy'),
        ('FLOAT', 'normalised_entropy'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Shannon entropy of the height or slope distribution. "
        "H = -\u03a3 p\u00b7ln(p)."
    )

    KEYWORDS = ("shannon", "information", "disorder")

    def process(self, field: DataField, mode: str, n_bins: int) -> tuple:
        n_bins = max(16, int(n_bins))
        data = np.asarray(field.data, dtype=np.float64)

        if mode == "slope magnitude":
            # Compute slope magnitude from Sobel-like finite differences.
            # Central differences along x and y (axis=1 and axis=0).
            # np.gradient uses central differences, same spirit as Sobel.
            dy, dx = np.gradient(data)
            values = np.hypot(dx, dy).ravel()
        else:
            values = data.ravel()

        # Remove non-finite values before binning.
        values = values[np.isfinite(values)]

        if values.size == 0:
            h = 0.0
            h_norm = 0.0
        else:
            counts, _ = np.histogram(values, bins=n_bins)
            total = counts.sum()
            if total == 0:
                h = 0.0
                h_norm = 0.0
            else:
                # Probability distribution; skip zero bins.
                p = counts[counts > 0].astype(np.float64) / float(total)
                h = float(-np.sum(p * np.log(p)))
                # Maximum possible entropy for n_bins equally occupied bins is ln(n_bins).
                h_max = float(np.log(n_bins))
                h_norm = h / h_max if h_max > 0.0 else 0.0

        table = RecordTable([
            {"quantity": "entropy",            "value": h,      "unit": "nat"},
            {"quantity": "normalised entropy", "value": h_norm, "unit": ""},
            {"quantity": "mode",               "value": mode,   "unit": ""},
            {"quantity": "n_bins",             "value": n_bins, "unit": ""},
        ])
        emit_table(table)

        return (h, h_norm)
