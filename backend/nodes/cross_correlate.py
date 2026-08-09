from __future__ import annotations

import numpy as np

from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.node_registry import register_node


@register_node(display_name="Cross-Correlate")
class CrossCorrelate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "mode": (["full", "same", "valid"], {"default": "same"}),
                "normalize": ("BOOLEAN", {"default": True}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'correlation'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute 2D cross-correlation between two fields. The correlation peak indicates "
        "the offset where the two fields best match. Useful for drift measurement and feature "
        "alignment. The measurement table reports the pixel shift (dx, dy) of field_b relative "
        "to field_a — the amount field_b must be shifted to align with field_a — in pixels and "
        "physical units, plus the normalized peak correlation coefficient."
    )

    KEYWORDS = ("xcorr", "alignment", "registration", "drift", "match")

    def process(
        self,
        field_a: DataField,
        field_b: DataField,
        mode: str,
        normalize: bool,
    ) -> tuple:
        from scipy.signal import fftconvolve

        a = field_a.data - field_a.data.mean()
        b = field_b.data - field_b.data.mean()

        # Cross-correlation via FFT: correlate(a,b) = ifft(fft(a) * conj(fft(b)))
        # Achieved by convolving a with the flipped b
        corr = fftconvolve(a, b[::-1, ::-1], mode=mode)

        denom = np.sqrt((a ** 2).sum() * (b ** 2).sum())

        # Estimate the alignment shift from a full-mode correlation, whose peak is
        # unambiguous for every output mode (mode="valid" can collapse to a single pixel).
        corr_full = fftconvolve(a, b[::-1, ::-1], mode="full")
        peak_y, peak_x = np.unravel_index(np.argmax(corr_full), corr_full.shape)
        # Zero lag of the full correlation sits at (Na-1, Ma-1). The peak offset from it
        # is the shift that must be applied to field_b to align it with field_a.
        dy = float(peak_y - (a.shape[0] - 1))
        dx = float(peak_x - (a.shape[1] - 1))

        coeff = float(corr_full[peak_y, peak_x]) / denom if normalize and denom > 0 else float(corr_full[peak_y, peak_x])

        measurement = RecordTable([
            {"quantity": "Shift X", "value": dx * field_a.dx, "unit": field_a.si_unit_xy},
            {"quantity": "Shift Y", "value": dy * field_a.dy, "unit": field_a.si_unit_xy},
            {"quantity": "Shift X (px)", "value": dx, "unit": "px"},
            {"quantity": "Shift Y (px)", "value": dy, "unit": "px"},
            {"quantity": "Peak correlation", "value": coeff, "unit": ""},
        ])
        emit_table(measurement)

        if normalize and denom > 0:
            corr = corr / denom

        if mode == "same":
            # Output is the same shape as field_a — reuse its physical dimensions
            return (field_a.replace(data=corr), measurement)

        # For "full" mode: output shape is (Na+Nb-1, Ma+Mb-1)
        # Scale physical dimensions proportionally
        na, ma = field_a.data.shape
        nb, mb = field_b.data.shape
        out_y, out_x = corr.shape

        # Physical size per pixel stays the same as field_a; total physical size scales
        new_xreal = field_a.xreal * out_x / ma if ma > 0 else field_a.xreal
        new_yreal = field_a.yreal * out_y / na if na > 0 else field_a.yreal

        return (field_a.replace(data=corr, xreal=new_xreal, yreal=new_yreal), measurement)
