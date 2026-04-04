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
                "cutoff": ("FLOAT", {"default": 0.1, "min": 0.001, "max": 0.5, "step": 0.001}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'low_pass'),
        ('DATA_FIELD', 'high_pass'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Separate a field into low-frequency (background) and high-frequency "
        "(detail) components using FFT. The cutoff is relative to the Nyquist "
        "frequency (0.5 = no filtering, 0.001 = very aggressive). "
    )

    def process(self, field: DataField, cutoff: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        kx = np.fft.fftfreq(xres)
        ky = np.fft.fftfreq(yres)
        KX, KY = np.meshgrid(kx, ky)
        K = np.sqrt(KX**2 + KY**2)

        # Gaussian low-pass filter
        lp_filter = np.exp(-0.5 * (K / cutoff)**2)

        fft_data = np.fft.fft2(data)
        low = np.real(np.fft.ifft2(fft_data * lp_filter))
        high = data - low

        return (field.replace(data=low), field.replace(data=high))
