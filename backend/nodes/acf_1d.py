from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import LineData, MeasureTable
from backend.nodes.spectral_common import acf_line_from_data


def _first_positive_peak(acf: np.ndarray, lag_axis: np.ndarray) -> float | None:
    """Return the lag of the first local maximum in the positive-lag half of the ACF."""
    center = len(acf) // 2
    pos_acf = acf[center + 1:]
    pos_lags = lag_axis[center + 1:]
    for i in range(1, len(pos_acf) - 1):
        if pos_acf[i] >= pos_acf[i - 1] and pos_acf[i] > pos_acf[i + 1]:
            return float(pos_lags[i])
    return None


@register_node(display_name="ACF 1D")
class ACF1D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "profile": ("LINE", {
                    "label": "input",
                    "accepted_types": ["LINE"],
                }),
                "level": (["mean", "none"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('LINE', 'acf'),
        ('MEASURE_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the one-dimensional autocorrelation function of a line profile. "
        "The output is symmetric about zero lag with the lag on the x-axis. "
        "The measurement table reports the dominant period from the first positive peak."
    )

    def process(self, profile: LineData, level: str) -> tuple:
        z = np.asarray(profile, dtype=np.float64)
        if level == "mean":
            z = z - z.mean()

        acf_line = acf_line_from_data(profile, z)

        x_unit = profile.x_unit if isinstance(profile, LineData) else ""
        peak_lag = _first_positive_peak(acf_line.data, acf_line.x_axis)

        rows = []
        if peak_lag is not None:
            rows.append({"quantity": "Peak period", "value": peak_lag, "unit": x_unit})

        return (acf_line, MeasureTable(rows))
