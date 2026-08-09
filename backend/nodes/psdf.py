from __future__ import annotations

import numpy as np

from backend.execution_context import emit_table
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.nodes.spectral_common import preprocess_spectral_data, psdf_field_from_data


@register_node(display_name="PSDF")
class PSDF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "windowing": (["hann", "hamming", "blackman", "none"], {"default": "hann"}),
                "level": (["mean", "plane", "none"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'psdf'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the two-dimensional power spectral density function with window "
        "RMS compensation and centered zero frequency. Also reports the total RMS "
        "roughness recovered from the PSD."
    )

    KEYWORDS = ("power spectrum", "fourier", "frequency", "roughness", "spectral density")

    def process(self, field: DataField, windowing: str, level: str) -> tuple:
        data = preprocess_spectral_data(field, level=level, windowing=windowing)
        psdf_field = psdf_field_from_data(field, data)
        # Total variance = integral of the PSD over frequency space. The PSDF field's
        # xreal/yreal are the full 2*pi/dx k-range, so the bin width uses the PHYSICAL
        # extents (2*pi/xreal) instead; Parseval then makes rms == sqrt(mean(z^2)).
        rms = float(
            np.sqrt(
                np.sum(
                    psdf_field.data
                    * (2.0 * np.pi / field.xreal)
                    * (2.0 * np.pi / field.yreal)
                )
            )
        )
        measurement = RecordTable([
            {"quantity": "RMS roughness", "value": rms, "unit": field.si_unit_z},
        ])
        emit_table(measurement)
        return (psdf_field, measurement)
