"""Grain cross-correlation — scatter plots of grain properties between two fields."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Grain Cross")
class GrainCross:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "property_a": (["area", "mean_height", "max_height", "volume"],
                               {"default": "mean_height"}),
                "property_b": (["area", "mean_height", "max_height", "volume"],
                               {"default": "max_height"}),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'correlation'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Correlate grain properties between two fields using a shared mask. "
        "Outputs a table of (property_a, property_b) pairs for each grain, "
        "plus Pearson correlation coefficient. "
    )

    KEYWORDS = ("pearson", "scatter", "correlate", "property")

    def process(self, field_a: DataField, field_b: DataField, mask: np.ndarray,
                property_a: str, property_b: str, min_size: int) -> tuple:
        data_a = np.asarray(field_a.data, dtype=np.float64)
        data_b = np.asarray(field_b.data, dtype=np.float64)
        grain = mask_to_bool(mask)
        labeled, n_grains = label(grain.astype(np.int32))

        pixel_area = field_a.dx * field_a.dy

        def _get_prop(data, gpx, prop):
            n_px = gpx.sum()
            if prop == "area":
                return n_px * pixel_area
            elif prop == "mean_height":
                return float(data[gpx].mean())
            elif prop == "max_height":
                return float(data[gpx].max())
            elif prop == "volume":
                base = float(data[~grain].mean()) if (~grain).any() else 0.0
                return float(np.sum(data[gpx] - base) * pixel_area)
            return 0.0

        vals_a, vals_b = [], []
        records = RecordTable()
        for gid in range(1, n_grains + 1):
            gpx = labeled == gid
            if gpx.sum() < min_size:
                continue
            va = _get_prop(data_a, gpx, property_a)
            vb = _get_prop(data_b, gpx, property_b)
            vals_a.append(va)
            vals_b.append(vb)
            records.append({
                "quantity": f"Grain {gid}",
                "value": f"{va:.4g} / {vb:.4g}",
                "unit": f"{property_a} / {property_b}",
            })

        # Pearson correlation
        if len(vals_a) >= 2:
            corr = float(np.corrcoef(vals_a, vals_b)[0, 1])
            records.append({"quantity": "Pearson r", "value": f"{corr:.4f}", "unit": ""})

        return (records,)
