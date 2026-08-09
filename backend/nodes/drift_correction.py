"""Drift correction — compensate for thermal/piezo drift between scan lines."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import shift as ndimage_shift

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _estimate_drift(data: np.ndarray, reference: str) -> np.ndarray:
    """Estimate per-row horizontal drift via cross-correlation with a reference.

    Returns an array of shape (yres,) with the estimated x-shift (in pixels)
    for each row.
    """
    yres, xres = data.shape
    shifts = np.zeros(yres)

    if reference == "previous_row":
        for i in range(1, yres):
            corr = np.correlate(data[i - 1], data[i], mode="full")
            peak = np.argmax(corr) - (xres - 1)
            shifts[i] = shifts[i - 1] + peak
    elif reference == "mean_row":
        mean_row = data.mean(axis=0)
        for i in range(yres):
            corr = np.correlate(mean_row, data[i], mode="full")
            peak = np.argmax(corr) - (xres - 1)
            shifts[i] = peak
    else:
        raise ValueError(f"Unknown reference: {reference!r}")

    # Remove the overall mean to centre the correction
    shifts -= shifts.mean()
    return shifts


@register_node(display_name="Drift Correction")
class DriftCorrection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "reference": (["previous_row", "mean_row"], {"default": "previous_row"}),
                "direction": (["horizontal", "vertical"], {"default": "horizontal"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
        ('RECORD_TABLE', 'drift'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compensate for thermal or piezo drift between scan lines. "
        "Cross-correlates each row (or column) against a reference to estimate "
        "the drift offset, then shifts lines to correct. "
        "The drift table reports max, mean |drift|, and RMS drift in pixels, "
        "plus the max drift in physical units along the corrected direction."
    )

    KEYWORDS = ("thermal", "piezo", "alignment", "shift", "row")

    def process(self, field: DataField, reference: str, direction: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        if direction == "vertical":
            data = data.T

        shifts = _estimate_drift(data, reference)
        corrected = np.empty_like(data)
        for i, s in enumerate(shifts):
            if abs(s) < 0.01:
                corrected[i] = data[i]
            else:
                ndimage_shift(data[i], -s, output=corrected[i], mode="reflect")

        if direction == "vertical":
            corrected = corrected.T

        shifts_abs = np.abs(shifts)
        scale = field.dx if direction == "horizontal" else field.dy
        rows = [
            {"quantity": "Max drift (px)", "value": float(np.max(shifts_abs)), "unit": "px"},
            {"quantity": "Mean |drift| (px)", "value": float(np.mean(shifts_abs)), "unit": "px"},
            {"quantity": "RMS drift (px)", "value": float(np.sqrt(np.mean(shifts ** 2))), "unit": "px"},
            {"quantity": "Max drift", "value": float(np.max(shifts_abs)) * scale, "unit": field.si_unit_xy},
        ]
        drift = RecordTable(rows)
        emit_table(drift)
        return (field.replace(data=corrected), drift)
