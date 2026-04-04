"""Deconvolution — image restoration via regularised deconvolution."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Deconvolution")
class Deconvolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["wiener", "richardson_lucy"], {"default": "wiener"}),
                "sigma": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 50.0, "step": 0.1}),
                "regularisation": ("FLOAT", {"default": 0.01, "min": 1e-6, "max": 1.0, "step": 0.001}),
                "iterations": ("INT", {"default": 10, "min": 1, "max": 200}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'restored'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Restore an image via regularised deconvolution. Assumes the image was "
        "blurred by a Gaussian PSF with the given sigma (in pixels). "
        "Wiener filtering is fast and works in one pass. "
        "Richardson-Lucy is iterative and preserves positivity. "
        "Equivalent to Gwyddion's deconvolve.c module."
    )

    def process(
        self,
        field: DataField,
        method: str,
        sigma: float,
        regularisation: float,
        iterations: int,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Build Gaussian PSF in frequency domain
        kx = np.fft.fftfreq(xres)
        ky = np.fft.fftfreq(yres)
        KX, KY = np.meshgrid(kx, ky)
        K2 = KX**2 + KY**2
        H = np.exp(-2.0 * (np.pi * sigma)**2 * K2)

        if method == "wiener":
            fft_data = np.fft.fft2(data)
            H2 = H * H
            # Wiener filter: H* / (|H|² + λ)
            wiener = np.conj(H) / (H2 + regularisation)
            restored = np.real(np.fft.ifft2(fft_data * wiener))

        elif method == "richardson_lucy":
            # Richardson-Lucy iterative deconvolution
            estimate = data.copy()
            H_conj = np.conj(H)

            for _ in range(iterations):
                estimate = np.maximum(estimate, 1e-30)  # positivity
                blurred = np.real(np.fft.ifft2(np.fft.fft2(estimate) * H))
                blurred = np.maximum(blurred, 1e-30)
                ratio = data / blurred
                correction = np.real(np.fft.ifft2(np.fft.fft2(ratio) * H_conj))
                estimate = estimate * correction

            restored = estimate
        else:
            raise ValueError(f"Unknown deconvolution method: {method!r}")

        return (field.replace(data=restored),)
