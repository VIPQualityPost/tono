from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.spectral_common import (
    preprocess_spectral_data,
    psdf_field_from_data,
    spatial_frequency_field,
)


@register_node(display_name="2D FFT")
class FFT2D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "windowing": (["hann", "hamming", "blackman", "none"],),
                "level": (["mean", "plane", "none"],),
            }
        }

    RETURN_TYPES = ("DATA_FIELD", "DATA_FIELD", "DATA_FIELD", "DATA_FIELD")
    RETURN_NAMES = ("log_magnitude", "magnitude", "phase", "psdf")
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the 2D FFT with optional windowing and mean/plane subtraction. "
        "Outputs log magnitude, magnitude, phase, and PSDF as separate channels. "
        "Equivalent to gwy_data_field_2dfft / gwy_data_field_2dpsdf."
    )

    def process(self, field: DataField, windowing: str, level: str) -> tuple:
        data = preprocess_spectral_data(field, level=level, windowing=windowing)
        F = np.fft.fftshift(np.fft.fft2(data))

        magnitude = np.abs(F)
        log_magnitude = np.log1p(magnitude)
        phase = np.angle(F)

        return (
            spatial_frequency_field(field, log_magnitude),
            spatial_frequency_field(field, magnitude),
            spatial_frequency_field(field, phase),
            psdf_field_from_data(field, data),
        )
