from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import LineData, RecordTable


@register_node(display_name="FFT 1D")
class FFT1D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "profile": ("LINE", {
                    "label": "input",
                    "accepted_types": ["LINE"],
                }),
            }
        }
    
    OUTPUTS = (
        ("LINE", "frequency_plot"),
        ('RECORD_TABLE', 'max'),
    )

    FUNCTION = "process"

    DESCRIPTION = (
        "Returns the FFT spectrum of the line, and identifies peaks."
    )

    def process(
            self, profile,
    ) -> tuple:
        line_data = np.asarray(profile, dtype=np.float64)
        n = len(line_data)

        if isinstance(profile, LineData) and profile.x_axis is not None and len(profile.x_axis) > 1:
            d = float(profile.x_axis[1] - profile.x_axis[0])
            spatial_unit = profile.x_unit or "m"
        else:
            d = 1.0
            spatial_unit = "m"

        spectrum = np.abs(np.fft.rfft(line_data))
        freq_axis = np.fft.rfftfreq(n, d)

        # Exclude DC component, convert to period, sort short→long
        spectrum = spectrum[1:][::-1]
        period_axis = (1.0 / freq_axis[1:])[::-1]

        peak_period = float(period_axis[np.argmax(spectrum)])

        table = RecordTable([
            {"quantity": "Peak period", "value": peak_period, "unit": spatial_unit},
        ])

        return (
            LineData(
                data=spectrum,
                x_axis=period_axis,
                x_unit=spatial_unit,
                y_unit=profile.y_unit if isinstance(profile, LineData) else "",
            ),
            table,
        )
