"""Grain property distributions — compute histograms of grain properties."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label

from backend.node_registry import register_node
from backend.data_types import DataField, LineData
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Grain Distributions")
class GrainDistributions:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "property": (["area", "equiv_diameter", "mean_height", "max_height",
                              "volume", "boundary_length"], {"default": "area"}),
                "n_bins": ("INT", {"default": 30, "min": 5, "max": 200, "step": 1}),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('LINE_DATA', 'distribution'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute a histogram of a grain property from a labeled mask. "
        "Supported properties: area, equivalent diameter, mean height, "
        "max height, volume, and boundary length. "
    )

    KEYWORDS = ("histogram", "particle", "diameter", "area", "volume")

    def process(self, field: DataField, mask: np.ndarray, property: str,
                n_bins: int, min_size: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        grain_mask = mask_to_bool(mask)
        labeled, n_grains = label(grain_mask.astype(np.int32))

        pixel_area = field.dx * field.dy
        xy_unit = field.si_unit_xy or "m"
        z_unit = field.si_unit_z or "m"

        values = []
        for gid in range(1, n_grains + 1):
            gpx = labeled == gid
            n_px = int(gpx.sum())
            if n_px < min_size:
                continue

            if property == "area":
                values.append(n_px * pixel_area)
            elif property == "equiv_diameter":
                area = n_px * pixel_area
                values.append(2.0 * np.sqrt(area / np.pi))
            elif property == "mean_height":
                values.append(float(data[gpx].mean()))
            elif property == "max_height":
                values.append(float(data[gpx].max()))
            elif property == "volume":
                base = float(data[~grain_mask].mean()) if (~grain_mask).any() else 0.0
                values.append(float(np.sum(data[gpx] - base) * pixel_area))
            elif property == "boundary_length":
                # Count boundary pixels (pixels with at least one non-grain neighbor)
                padded = np.pad(gpx, 1, mode='constant', constant_values=False)
                boundary = gpx & ~(
                    padded[:-2, 1:-1] & padded[2:, 1:-1] &
                    padded[1:-1, :-2] & padded[1:-1, 2:]
                )
                values.append(int(boundary.sum()) * max(field.dx, field.dy))

        if len(values) == 0:
            values = [0.0]

        # Unit labels
        unit_map = {
            "area": f"{xy_unit}²",
            "equiv_diameter": xy_unit,
            "mean_height": z_unit,
            "max_height": z_unit,
            "volume": f"{xy_unit}²·{z_unit}",
            "boundary_length": xy_unit,
        }

        arr = np.array(values)
        counts, edges = np.histogram(arr, bins=n_bins)
        centers = 0.5 * (edges[:-1] + edges[1:])

        return (LineData(
            data=counts.astype(np.float64),
            x_axis=centers,
            x_unit=unit_map.get(property, ""),
            y_unit="count",
        ),)
