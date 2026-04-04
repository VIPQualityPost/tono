"""Grain marking — mark grains by height, slope, or curvature criteria."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label, sobel

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask


@register_node(display_name="Grain Mark")
class GrainMark:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "criterion": (["height", "slope", "curvature"], {"default": "height"}),
                "threshold_low": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01}),
                "threshold_high": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "min_size": ("INT", {"default": 10, "min": 1, "max": 100000, "step": 1}),
                "inverted": ("BOOLEAN", {"default": False}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Mark grains by thresholding height, slope magnitude, or curvature. "
        "Thresholds are relative (0–1) to the data range. Small regions below "
        "min_size pixels are removed. Use inverted to mark valleys instead of peaks. "
    )

    def process(self, field: DataField, criterion: str, threshold_low: float,
                threshold_high: float, min_size: int, inverted: bool) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if criterion == "height":
            values = data
        elif criterion == "slope":
            gx = sobel(data, axis=1)
            gy = sobel(data, axis=0)
            values = np.sqrt(gx**2 + gy**2)
        elif criterion == "curvature":
            gxx = sobel(sobel(data, axis=1), axis=1)
            gyy = sobel(sobel(data, axis=0), axis=0)
            values = np.abs(gxx + gyy)
        else:
            raise ValueError(f"Unknown criterion: {criterion!r}")

        # Normalize to [0, 1]
        vmin, vmax = values.min(), values.max()
        if vmax > vmin:
            norm = (values - vmin) / (vmax - vmin)
        else:
            norm = np.zeros_like(values)

        # Apply thresholds
        binary = (norm >= threshold_low) & (norm <= threshold_high)

        if inverted:
            binary = ~binary

        # Remove small regions
        labeled, n_labels = label(binary.astype(np.int32))
        for gid in range(1, n_labels + 1):
            if (labeled == gid).sum() < min_size:
                binary[labeled == gid] = False

        return (bool_to_mask(binary),)
