from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, LineData
from backend.nodes.helpers import _cached_1d_transfer, _cached_2d_transfer


@register_node(display_name="FFT Filter")
class FFTFilter:
    """Frequency-domain filtering of a line profile or 2-D data field.

    Accepts either a LINE or DATA_FIELD and returns a filtered output of the
    same type.  Uses a Butterworth transfer function with configurable order
    for a smooth roll-off.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("LINE", {
                    "label": "input",
                    "accepted_types": ["DATA_FIELD"],
                }),
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

    OUTPUTS = (
        ('LINE', 'filtered', {"accepted_types": ["DATA_FIELD"]}),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Frequency-domain filtering of a line profile or 2-D data field. "
        "Connect a LINE for 1-D filtering or a DATA_FIELD for 2-D filtering — "
        "the output mirrors the input type. "
        "Supports lowpass, highpass, bandpass, and notch (band-reject) modes "
        "with a Butterworth roll-off. Cutoffs are fractions of the Nyquist frequency."
    )

    def process(self, input, filter_type: str, cutoff: float,
                cutoff_high: float, order: int) -> tuple:
        if isinstance(input, DataField):
            return self._process_field(input, filter_type, float(cutoff), float(cutoff_high), int(order))
        return self._process_line(input, filter_type, float(cutoff), float(cutoff_high), int(order))

    def _process_line(self, line, filter_type: str, cutoff: float,
                      cutoff_high: float, order: int) -> tuple:
        z = np.asarray(line, dtype=np.float64).ravel()
        n = len(z)

        Z = np.fft.rfft(z)
        H = _cached_1d_transfer(n, filter_type, cutoff, cutoff_high, order)
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

    def _process_field(self, field: DataField, filter_type: str, cutoff: float,
                       cutoff_high: float, order: int) -> tuple:
        data = field.data
        yres, xres = data.shape

        mean_val = float(data.mean())
        centered = data - mean_val

        spectrum = np.fft.rfft2(centered)
        transfer = _cached_2d_transfer(yres, xres, filter_type, cutoff, cutoff_high, order)
        result = np.fft.irfft2(spectrum * transfer, s=(yres, xres))
        result += mean_val

        return (field.replace(data=result),)
