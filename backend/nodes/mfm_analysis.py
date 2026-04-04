"""MFM analysis — magnetic force microscopy field calculations."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="MFM Analysis")
class MFMAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "operation": (["phase_to_force_gradient", "force_gradient_to_field",
                               "charge_density", "magnetisation"],),
                "lift_height": ("FLOAT", {
                    "default": 50e-9, "min": 1e-9, "max": 1e-6, "step": 1e-9,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Magnetic force microscopy analysis. Converts MFM phase or frequency "
        "shift data into physical quantities using Fourier-domain transfer "
        "functions. Operations: phase_to_force_gradient converts phase to "
        "d²F/dz²; force_gradient_to_field recovers the stray field Hz; "
        "charge_density computes the effective magnetic charge; "
        "magnetisation estimates the z-component of sample magnetisation. "
    )

    def process(self, field: DataField, operation: str, lift_height: float) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Build frequency grids
        kx = np.fft.fftfreq(xres, d=field.dx) * 2 * np.pi
        ky = np.fft.fftfreq(yres, d=field.dy) * 2 * np.pi
        KX, KY = np.meshgrid(kx, ky)
        K = np.sqrt(KX**2 + KY**2)

        # Avoid division by zero at DC
        K_safe = np.where(K == 0, 1.0, K)

        fft_data = np.fft.fft2(data)

        if operation == "phase_to_force_gradient":
            # Phase ∝ F'' / k_cantilever, output is proportional to d²F/dz²
            # Just propagate to the surface by multiplying by exp(k*h)
            transfer = np.exp(K * lift_height)
            transfer[0, 0] = 1.0
            result = np.real(np.fft.ifft2(fft_data * transfer))
            z_unit = field.si_unit_z

        elif operation == "force_gradient_to_field":
            # Recover Hz from d²F/dz² using the relation in Fourier space:
            # Hz(k) = F''(k) * exp(k*h) / (μ₀ * k²)
            transfer = np.exp(K * lift_height) / (K_safe**2)
            transfer[0, 0] = 0.0  # remove DC
            result = np.real(np.fft.ifft2(fft_data * transfer))
            z_unit = "A/m"

        elif operation == "charge_density":
            # σ_m = -dHz/dz ∝ k * Hz in Fourier space
            transfer = K * np.exp(K * lift_height) / (K_safe**2)
            transfer[0, 0] = 0.0
            result = np.real(np.fft.ifft2(fft_data * transfer))
            z_unit = "A/m²"

        elif operation == "magnetisation":
            # Mz ∝ σ_m, further divide by k to integrate
            transfer = np.exp(K * lift_height) / K_safe
            transfer[0, 0] = 0.0
            result = np.real(np.fft.ifft2(fft_data * transfer))
            z_unit = "A/m"

        else:
            raise ValueError(f"Unknown MFM operation: {operation!r}")

        return (field.replace(data=result, si_unit_z=z_unit),)
