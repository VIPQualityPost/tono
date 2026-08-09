from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


def _cwt_scale_response(data: np.ndarray, scale_px: float, wavelet: str) -> np.ndarray:
    """CWT response of *data* at a single scale.

    Faithful port of Gwyddion's `gwy_data_field_cwt` (libprocess/cwt.c): the field
    is transformed with a plain FFT (rect windowing), multiplied in the frequency
    domain by the radially symmetric wavelet `gwy_cwt_wfunc_2d` (libprocess/cwt.c)
    sampled on Gwyddion's raw-FFT frequency grid (DC in the corner, negative
    frequencies wrapped), and transformed back.  Gwyddion uses symmetric FFT
    normalisation, which nets out to plain np.fft.fft2/np.fft.ifft2 for the real
    output, so no extra scaling factor is needed.
    """
    yres, xres = data.shape
    fft = np.fft.fft2(data)

    # Radial frequency index mval = hypot(min(i, yres-i), min(j, xres-j)) —
    # exactly the per-pixel frequency layout used by gwy_data_field_mult_wav().
    i, j = np.indices(data.shape)
    mval = np.hypot(np.minimum(i, yres - i), np.minimum(j, xres - j)).astype(np.float64)

    dat2x = 4.0 / xres
    cur = mval * dat2x
    cur2 = cur * cur
    scale2 = scale_px * scale_px
    if wavelet == "gaussian":
        # GWY_2DCWT_GAUSS: exp(-(scale^2 * cur^2)/2)
        wav = np.exp(-0.5 * scale2 * cur2)
    else:  # mexican_hat — GWY_2DCWT_HAT: (scale^2*cur^2) * exp(-(scale^2*cur^2)/2) * 2*pi*scale^2
        wav = (scale2 * cur2) * np.exp(-0.5 * scale2 * cur2) * 2.0 * np.pi * scale2

    return np.fft.ifft2(fft * wav).real


@register_node(display_name="2D CWT")
class CWT2D:
    CATEGORY = "Spectral"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "wavelet": (["gaussian", "mexican_hat"], {"default": "mexican_hat"}),
                "min_scale_px": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 1000.0, "step": 0.5}),
                "max_scale_px": ("FLOAT", {"default": 20.0, "min": 0.1, "max": 1000.0, "step": 0.5}),
                "n_scales": ("INT", {"default": 10, "min": 1, "max": 256}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'transform'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the two-dimensional continuous wavelet transform (CWT) of a field "
        "and output the maximum wavelet response across a sweep of scales. The "
        "wavelet is applied in the Fourier domain, exactly as Gwyddion's 2D CWT "
        "module. A Gaussian wavelet is a scale-selective low-pass filter while the "
        "Mexican hat is a scale-selective band-pass; features whose lateral size "
        "matches a scale in the sweep produce strong response at that scale."
    )

    KEYWORDS = ("cwt", "wavelet", "continuous", "scale", "mexican hat", "gaussian", "fourier")

    def process(
        self,
        field: DataField,
        wavelet: str,
        min_scale_px: float,
        max_scale_px: float,
        n_scales: int,
    ) -> tuple:
        if wavelet not in ("gaussian", "mexican_hat"):
            raise ValueError(f"Unknown wavelet type: {wavelet}")
        if n_scales < 1:
            raise ValueError(f"n_scales must be a positive integer, got {n_scales}")
        if min_scale_px <= 0.0 or max_scale_px <= 0.0:
            raise ValueError("Scale bounds must be positive")
        if min_scale_px > max_scale_px:
            raise ValueError(
                f"min_scale_px ({min_scale_px}) must not exceed max_scale_px ({max_scale_px})"
            )

        scales = np.linspace(float(min_scale_px), float(max_scale_px), int(n_scales))
        responses = [_cwt_scale_response(field.data, float(s), wavelet) for s in scales]
        # Maximum-over-scales absolute response: Gwyddion shows the single-scale CWT
        # live as the scale slider is swept; the node freezes that into one field.
        response = np.maximum.reduce([np.abs(r) for r in responses])

        return (field.replace(data=response),)
