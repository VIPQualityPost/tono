"""MFM Domain Generation — stray field from parallel magnetic stripe domains."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="MFM Domain Generation")
class MFMDomainGeneration:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "height": ("FLOAT", {
                    "default": 50e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "thickness": ("FLOAT", {
                    "default": 20e-9, "min": 1e-9, "max": 1e-6, "step": 1e-9,
                }),
                "magnetization": ("FLOAT", {
                    "default": 1e6, "min": 1.0, "max": 1e8, "step": 1.0,
                }),
                "stripe_width_a": ("FLOAT", {
                    "default": 200e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
                "stripe_width_b": ("FLOAT", {
                    "default": 200e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
                "gap": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 10e-6, "step": 1e-9,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'hz'),
        ('DATA_FIELD', 'dhz_dz'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Generates the stray field from parallel magnetic stripe domains with "
        "alternating up/down magnetization along x, uniform along y. Computes "
        "both the normal component Hz and its vertical gradient dHz/dz using "
        "FFT-based transfer functions, suitable for MFM simulation and testing. "
    )

    def process(
        self,
        field: DataField,
        height: float,
        thickness: float,
        magnetization: float,
        stripe_width_a: float,
        stripe_width_b: float,
        gap: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # --- 1. Build 1D magnetization profile along x ---
        x = np.linspace(0, field.xreal, xres, endpoint=False)
        period = stripe_width_a + stripe_width_b + 2 * gap

        x_mod = x % period
        m_1d = np.zeros(xres, dtype=np.float64)

        # Domain A: +M
        mask_a = x_mod < stripe_width_a
        m_1d[mask_a] = magnetization

        # Domain B: -M
        b_start = stripe_width_a + gap
        b_end = stripe_width_a + gap + stripe_width_b
        mask_b = (x_mod >= b_start) & (x_mod < b_end)
        m_1d[mask_b] = -magnetization

        # Gaps remain zero

        # --- 2. FFT of the magnetization profile ---
        M_k = np.fft.rfft(m_1d)
        kx = np.fft.rfftfreq(xres, d=field.dx) * 2 * np.pi
        k_abs = np.abs(kx)

        # Avoid division by zero at DC
        k_safe = np.where(k_abs == 0, 1.0, k_abs)

        # --- 3. Transfer function for Hz ---
        # Hz(k, z) = -(1/2) * exp(-|k|*z) * (1 - exp(-|k|*t)) * M(k)
        transfer_hz = -0.5 * np.exp(-k_abs * height) * (1 - np.exp(-k_safe * thickness))
        transfer_hz[0] = 0.0  # no DC component

        Hz_1d = np.fft.irfft(M_k * transfer_hz, n=xres)

        # --- 4. Transfer function for dHz/dz ---
        # d/dz[exp(-k*z)] = -k * exp(-k*z), so the derivative adds a factor of -(-k) = k
        # but with the negative sign in Hz: dHz/dz picks up an extra factor of k_abs
        transfer_dhz = 0.5 * k_abs * np.exp(-k_abs * height) * (1 - np.exp(-k_safe * thickness))
        transfer_dhz[0] = 0.0

        dHz_dz_1d = np.fft.irfft(M_k * transfer_dhz, n=xres)

        # --- 5. Tile to 2D (uniform along y) ---
        Hz = np.tile(Hz_1d, (yres, 1))
        dHz_dz = np.tile(dHz_dz_1d, (yres, 1))

        # --- 6. Build output DataFields ---
        hz_field = field.replace(data=Hz, si_unit_z="A/m")
        dhz_dz_field = field.replace(data=dHz_dz, si_unit_z="A/m²")

        return (hz_field, dhz_dz_field)
