"""Fractal interpolation — fill masked regions using fractal (self-similar) synthesis."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool


@register_node(display_name="Fractal Interpolation")
class FractalInterpolation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "iterations": ("INT", {"default": 200, "min": 10, "max": 5000, "step": 10}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'filled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fill masked regions using fractal interpolation. Matches the spectral "
        "characteristics of the surrounding surface to produce natural-looking "
        "infill that preserves texture. Better than Laplace for rough surfaces. "
    )

    KEYWORDS = ("inpaint", "fill", "hole", "infill")

    def process(self, field: DataField, mask: np.ndarray, iterations: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64).copy()
        hole = mask_to_bool(mask)

        if not hole.any():
            return (field.replace(data=data),)

        # Step 1: Estimate power spectrum from valid (unmasked) data
        valid_data = data.copy()
        valid_mean = data[~hole].mean() if (~hole).any() else 0.0
        valid_data[hole] = valid_mean

        fft_valid = np.fft.fft2(valid_data)
        power = np.abs(fft_valid) ** 2

        # Step 2: Generate fractal noise matching the power spectrum
        rng = np.random.default_rng(42)
        phases = rng.uniform(0, 2 * np.pi, data.shape)
        noise_fft = np.sqrt(power) * np.exp(1j * phases)
        noise = np.real(np.fft.ifft2(noise_fft))

        # Normalize noise to match local statistics around masked region
        if (~hole).any():
            noise = (noise - noise[~hole].mean()) / max(noise[~hole].std(), 1e-30) * \
                    data[~hole].std() + data[~hole].mean()

        # Step 3: Initialize masked pixels with fractal noise, then blend
        # with Laplace relaxation for smooth boundaries
        data[hole] = noise[hole]

        # Relax boundaries to ensure continuity
        padded = np.pad(data, 1, mode='edge')
        hole_padded = np.pad(hole, 1, mode='constant', constant_values=False)

        for _ in range(iterations):
            avg = (padded[:-2, 1:-1] + padded[2:, 1:-1] +
                   padded[1:-1, :-2] + padded[1:-1, 2:]) / 4.0
            # Blend: 90% fractal noise + 10% relaxation to smooth boundaries
            blend = 0.1
            new_vals = (1.0 - blend) * padded[1:-1, 1:-1][hole] + blend * avg[hole]
            padded[1:-1, 1:-1][hole] = new_vals

        data = padded[1:-1, 1:-1].copy()
        return (field.replace(data=data),)
