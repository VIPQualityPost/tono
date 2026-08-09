from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.nodes.acf_1d import _first_positive_peak
from backend.nodes.spectral_common import acf_field_from_data, preprocess_spectral_data


@register_node(display_name="ACF 2D")
class ACF2D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "level": (["mean", "plane", "none"], {"default": "mean"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'acf'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the two-dimensional autocorrelation function with Gwyddion-style "
        "mean or plane levelling before correlation. The output is centered on zero shift "
        "and uses the default half-range extents from acf2d. "
        "The measurement table reports the dominant period along each axis from the "
        "first positive peak of the center row and column."
    )

    KEYWORDS = ("autocorrelation", "correlation")

    def process(self, field: DataField, level: str) -> tuple:
        data = preprocess_spectral_data(field, level=level, windowing="none")
        acf_field = acf_field_from_data(field, data)
        acf = np.asarray(acf_field.data, dtype=np.float64)
        tyres, txres = acf.shape[0], acf.shape[1]

        lag_x = (np.arange(txres) - txres // 2) * field.dx
        lag_y = (np.arange(tyres) - tyres // 2) * field.dy

        rows = []
        period_x = _first_positive_peak(acf[tyres // 2, :], lag_x)
        period_y = _first_positive_peak(acf[:, txres // 2], lag_y)
        if period_x is not None:
            rows.append({"quantity": "Period x", "value": period_x, "unit": field.si_unit_xy})
        if period_y is not None:
            rows.append({"quantity": "Period y", "value": period_y, "unit": field.si_unit_xy})

        measurement = RecordTable(rows)
        emit_table(measurement)
        return (acf_field, measurement)
