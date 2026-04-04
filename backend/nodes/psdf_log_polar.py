"""Log-polar PSDF — power spectral density in log-polar coordinates."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Log-Polar PSDF")
class LogPolarPSDF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_phi": ("INT", {"default": 180, "min": 36, "max": 720, "step": 1}),
                "n_r": ("INT", {"default": 100, "min": 20, "max": 500, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'psdf'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the power spectral density function in log-polar coordinates. "
        "The x-axis is the azimuthal angle (0-360°) and y-axis is log(frequency). "
        "Better than Cartesian PSDF for anisotropy analysis. "
    )

    KEYWORDS = ("power spectrum", "azimuthal", "anisotropy", "directional", "fourier")

    def process(self, field: DataField, n_phi: int, n_r: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Compute 2D power spectrum
        fft = np.fft.fft2(data - data.mean())
        power = np.abs(np.fft.fftshift(fft))**2

        cy, cx = yres // 2, xres // 2

        # Build log-polar grid
        r_max = min(cx, cy)
        log_r = np.linspace(0, np.log(r_max), n_r)
        phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)

        result = np.zeros((n_r, n_phi))

        for ir in range(n_r):
            r = np.exp(log_r[ir])
            for ip in range(n_phi):
                fx = cx + r * np.cos(phi[ip])
                fy = cy + r * np.sin(phi[ip])
                # Bilinear interpolation
                ix = int(fx)
                iy = int(fy)
                if 0 <= ix < xres - 1 and 0 <= iy < yres - 1:
                    dx = fx - ix
                    dy = fy - iy
                    val = (power[iy, ix] * (1 - dx) * (1 - dy) +
                           power[iy, ix + 1] * dx * (1 - dy) +
                           power[iy + 1, ix] * (1 - dx) * dy +
                           power[iy + 1, ix + 1] * dx * dy)
                    result[ir, ip] = val

        # Log scale for display
        result = np.log1p(result)

        psdf_field = DataField(
            data=result,
            xreal=360.0,
            yreal=float(np.log(r_max)),
            si_unit_xy="deg",
            si_unit_z="",
            domain="frequency",
        )
        return (psdf_field,)
