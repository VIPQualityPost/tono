from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Wavelet Denoise")
class WaveletDenoise:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "wavelet": (
                    ["db1", "db2", "db4", "db8", "sym4", "coif1", "bior1.3"],
                    {"default": "db4"},
                ),
                "method": (["BayesShrink", "VisuShrink"], {"default": "BayesShrink"}),
                "sigma": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "mode": (["soft", "hard"], {"default": "soft"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'denoised'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Denoise using wavelet coefficient thresholding. BayesShrink adapts the threshold "
        "per sub-band; VisuShrink uses a global threshold."
    )

    def process(
        self,
        field: DataField,
        wavelet: str,
        method: str,
        sigma: float,
        mode: str,
    ) -> tuple:
        from skimage.restoration import denoise_wavelet

        d = field.data
        dmin = float(d.min())
        drange = float(np.ptp(d))

        if drange == 0:
            return (field,)

        norm = (d - dmin) / drange
        sigma_val = float(sigma) if sigma > 0 else None

        # `mode` is a Python builtin name; use threshold_mode locally to avoid shadowing
        threshold_mode = mode

        denoised_norm = denoise_wavelet(
            norm,
            wavelet=wavelet,
            method=method,
            mode=threshold_mode,
            sigma=sigma_val,
            rescale_sigma=True,
            channel_axis=None,
        )

        result = denoised_norm * drange + dmin
        return (field.replace(data=result),)
