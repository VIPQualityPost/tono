"""Grain summary statistics — aggregate statistics for all grains."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.nodes.helpers import mask_to_bool, _square_unit


@register_node(display_name="Grain Summary")
class GrainSummary:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('RECORD_TABLE', 'summary'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute aggregate statistics for all grains in a mask: count, density, "
        "coverage fraction, mean/median area, total volume, and height statistics. "
    )

    KEYWORDS = ("particle", "count", "density", "coverage", "statistics")

    def process(self, field: DataField, mask: np.ndarray, min_size: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        grain_mask = mask_to_bool(mask)
        labeled, n_grains = label(grain_mask.astype(np.int32))

        pixel_area = field.dx * field.dy
        total_area = field.xreal * field.yreal
        xy_unit = field.si_unit_xy or "m"
        z_unit = field.si_unit_z or "m"

        # Collect per-grain properties
        areas = []
        heights = []
        volumes = []
        base_height = float(data[~grain_mask].mean()) if (~grain_mask).any() else 0.0

        for gid in range(1, n_grains + 1):
            gpx = labeled == gid
            n_px = int(gpx.sum())
            if n_px < min_size:
                continue
            area = n_px * pixel_area
            areas.append(area)
            heights.append(float(data[gpx].mean()))
            volumes.append(float(np.sum(data[gpx] - base_height) * pixel_area))

        records = RecordTable()
        n_valid = len(areas)
        records.append({"quantity": "Grain count", "value": n_valid, "unit": ""})
        records.append({"quantity": "Grain density", "value": float(n_valid / total_area) if total_area > 0 else 0.0, "unit": f"1/{_square_unit(xy_unit)}"})

        coverage = sum(areas) / total_area if total_area > 0 else 0.0
        records.append({"quantity": "Coverage fraction", "value": float(coverage), "unit": ""})

        if n_valid > 0:
            records.append({"quantity": "Mean area", "value": float(np.mean(areas)), "unit": _square_unit(xy_unit)})
            records.append({"quantity": "Median area", "value": float(np.median(areas)), "unit": _square_unit(xy_unit)})
            records.append({"quantity": "Total volume", "value": float(sum(volumes)), "unit": f"{_square_unit(xy_unit)}·{z_unit}"})
            records.append({"quantity": "Mean height", "value": float(np.mean(heights)), "unit": z_unit})
            records.append({"quantity": "Median height", "value": float(np.median(heights)), "unit": z_unit})
            records.append({"quantity": "Max area", "value": float(max(areas)), "unit": _square_unit(xy_unit)})
            records.append({"quantity": "Min area", "value": float(min(areas)), "unit": _square_unit(xy_unit)})

        return (records,)
