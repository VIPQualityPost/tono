from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import _cached_2d_transfer


@register_node(display_name="2D FFT Filter")
class FFTFilter2D:
    """Frequency-domain filtering of 2-D data fields (images).

    Equivalent to Gwyddion's fft_filter_2d module.  Applies a radial
    Butterworth transfer function in the frequency domain to remove or
    isolate periodic features.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
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
        ('DATA_FIELD', 'filtered'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Frequency-domain filtering of a 2-D data field. "
        "Supports lowpass, highpass, bandpass, and notch (band-reject) modes "
        "with a radial Butterworth roll-off. Cutoffs are fractions of the "
        "Nyquist frequency. Use lowpass to smooth, highpass to sharpen, or "
        "bandpass/notch to isolate or remove periodic noise. "
        "Equivalent to Gwyddion fft_filter_2d."
    )

    def process(self, field: DataField, filter_type: str, cutoff: float,
                cutoff_high: float, order: int) -> tuple:
        data = field.data
        yres, xres = data.shape

        mean_val = float(data.mean())
        centered = data - mean_val

        spectrum = np.fft.rfft2(centered)
        transfer = _cached_2d_transfer(
            yres, xres, filter_type,
            float(cutoff), float(cutoff_high), int(order),
        )
        result = np.fft.irfft2(spectrum * transfer, s=(yres, xres))
        result += mean_val

        return (field.replace(data=result),)
