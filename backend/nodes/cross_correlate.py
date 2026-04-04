from __future__ import annotations

import numpy as np

from backend.data_types import DataField
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
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute 2D cross-correlation between two fields. The correlation peak indicates "
        "the offset where the two fields best match. Useful for drift measurement and feature "
        "alignment."
    )

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

        if normalize:
            denom = np.sqrt((a ** 2).sum() * (b ** 2).sum())
            if denom > 0:
                corr = corr / denom

        if mode == "same":
            # Output is the same shape as field_a — reuse its physical dimensions
            return (field_a.replace(data=corr),)

        # For "full" mode: output shape is (Na+Nb-1, Ma+Mb-1)
        # Scale physical dimensions proportionally
        na, ma = field_a.data.shape
        nb, mb = field_b.data.shape
        out_y, out_x = corr.shape

        # Physical size per pixel stays the same as field_a; total physical size scales
        new_xreal = field_a.xreal * out_x / ma if ma > 0 else field_a.xreal
        new_yreal = field_a.yreal * out_y / na if na > 0 else field_a.yreal

        return (field_a.replace(data=corr, xreal=new_xreal, yreal=new_yreal),)
