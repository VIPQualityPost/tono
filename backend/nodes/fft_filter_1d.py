from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import LineData
from backend.nodes.helpers import _cached_1d_transfer


@register_node(display_name="1D FFT Filter")
class FFTFilter1D:
    """Bandpass / lowpass / highpass / notch filtering of 1-D line profiles.

    Equivalent to Gwyddion's fft_filter_1d module.  Uses a Butterworth
    transfer function with configurable order for a smooth roll-off.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line": ("LINE",),
                "filter_type": (["lowpass", "highpass", "bandpass", "notch"],),
                "cutoff": ("FLOAT", {
                    "default": 0.1, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "cutoff_high": ("FLOAT", {
                    "default": 0.4, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "order": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
            }
        }

    RETURN_TYPES = ("LINE",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"

    DESCRIPTION = (
        "Frequency-domain filtering of a 1-D line profile. "
        "Supports lowpass, highpass, bandpass, and notch (band-reject) modes "
        "with a Butterworth roll-off. Cutoffs are fractions of the Nyquist frequency. "
        "Equivalent to Gwyddion fft_filter_1d."
    )

    def process(self, line, filter_type: str, cutoff: float,
                cutoff_high: float, order: int) -> tuple:
        z = np.asarray(line, dtype=np.float64).ravel()
        n = len(z)

        Z = np.fft.rfft(z)
        H = _cached_1d_transfer(n, filter_type, float(cutoff), float(cutoff_high), int(order))
        Z *= H
        filtered = np.fft.irfft(Z, n=n)

        if isinstance(line, LineData):
            return (
                LineData(
                    data=filtered,
                    x_axis=line.x_axis.copy() if line.x_axis is not None else None,
                    x_unit=line.x_unit,
                    y_unit=line.y_unit,
                ),
            )
        return (filtered,)
