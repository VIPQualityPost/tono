"""Unrotate — auto-detect and correct in-plane scan rotation."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import rotate as ndimage_rotate

from backend.node_registry import register_node
from backend.data_types import DataField


def _slope_angle_histogram(data: np.ndarray, n_bins: int = 3600) -> np.ndarray:
    """Compute histogram of local slope angles over [0, 2*pi)."""
    dy = np.diff(data, axis=0)[:, :-1]
    dx = np.diff(data, axis=1)[:-1, :]
    angles = np.arctan2(dy, dx) % (2 * np.pi)
    hist, _ = np.histogram(angles.ravel(), bins=n_bins, range=(0, 2 * np.pi))
    return hist.astype(np.float64)


def _find_dominant_angle(hist: np.ndarray, symmetry: int) -> float:
    """Find the rotation correction angle for a given symmetry order.

    Folds the histogram into one symmetry sector, finds the peak, and
    returns the offset to the nearest axis.
    """
    n_bins = len(hist)
    sector = n_bins // symmetry
    folded = np.zeros(sector, dtype=np.float64)
    for k in range(symmetry):
        start = k * sector
        end = start + sector
        if end <= n_bins:
            folded += hist[start:end]

    peak_bin = int(np.argmax(folded))
    bin_angle = (2 * np.pi / symmetry) / sector

    # The angle of the peak
    peak_angle = peak_bin * bin_angle

    # The nearest axis is at multiples of pi/symmetry
    axis_spacing = np.pi / symmetry
    nearest_axis = round(peak_angle / axis_spacing) * axis_spacing
    correction = nearest_axis - peak_angle

    return float(correction)


@register_node(display_name="Unrotate")
class Unrotate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "symmetry": (["2-fold", "3-fold", "4-fold", "6-fold"], {"default": "4-fold"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'leveled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Auto-detect and correct in-plane scan rotation. Computes a slope "
        "angle histogram, finds the dominant feature direction for the given "
        "symmetry, and rotates the image to align features with the axes."
    )

    KEYWORDS = ("rotation", "alignment", "angle", "symmetry", "crystal")

    def process(self, field: DataField, symmetry: str = "4-fold") -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        sym_order = int(symmetry[0])
        hist = _slope_angle_histogram(data)
        angle_rad = _find_dominant_angle(hist, sym_order)
        angle_deg = float(np.degrees(angle_rad))

        if abs(angle_deg) < 0.01:
            return (field,)

        rotated = ndimage_rotate(data, angle_deg, reshape=False, order=1,
                                 mode='nearest')

        return (field.replace(data=rotated),)
