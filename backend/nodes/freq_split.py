"""Frequency splitting — separate image into low-pass and high-pass components."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Frequency Split")
class FrequencySplit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "cutoff": ("FLOAT", {"default": 0.2, "min": 0.001, "max": 1.0, "step": 0.001}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'low_pass'),
        ('DATA_FIELD', 'high_pass'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Separate a field into low-frequency (background) and high-frequency "
        "(detail) components using an FFT Gaussian filter. The cutoff is the "
        "Gaussian sigma as a fraction of the Nyquist frequency — the same "
        "meaning as the FFTFilter slider: 1.0 leaves the spectrum effectively "
        "untouched, smaller values cut progressively more."
    )

    KEYWORDS = ("lowpass", "highpass", "decompose", "background", "detail")

    def process(self, field: DataField, cutoff: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        kx = np.fft.fftfreq(xres)
        ky = np.fft.fftfreq(yres)
        KX, KY = np.meshgrid(kx, ky)
        K = np.sqrt(KX**2 + KY**2)

        # cutoff is a fraction of Nyquist (0.5 cycles/pixel), matching the
        # FFTFilter slider semantics; convert to cycles/pixel for the kernel.
        sigma = cutoff * 0.5

        # Gaussian low-pass filter
        with np.errstate(divide="ignore"):
            lp_filter = np.exp(-0.5 * (K / sigma) ** 2)

        fft_data = np.fft.fft2(data)
        low = np.real(np.fft.ifft2(fft_data * lp_filter))
        high = data - low

        return (field.replace(data=low), field.replace(data=high))
