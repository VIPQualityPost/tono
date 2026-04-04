"""MFM Current Simulation — magnetic field from a current-carrying line."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField

# Vacuum permeability
MU_0 = 4.0e-7 * np.pi


@register_node(display_name="MFM Current Simulation")
class MFMCurrentSimulation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "height": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "current": ("FLOAT", {
                    "default": 1e-3, "min": 1e-9, "max": 1.0, "step": 1e-6,
                }),
                "width": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "tip_magnetization": ("FLOAT", {
                    "default": 1e5, "min": 1.0, "max": 1e8, "step": 1.0,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'hx'),
        ('DATA_FIELD', 'hz'),
        ('DATA_FIELD', 'force'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Simulates the magnetic field produced by an infinite current-carrying "
        "strip (running along the y-axis) and the resulting force on an MFM "
        "tip. Uses the Biot-Savart law for a flat strip of finite width to "
        "compute the Hx and Hz field components at a given observation height, "
        "then derives the z-force on a point-dipole tip from the analytical "
        "gradient dHz/dz."
    )

    def process(
        self,
        field: DataField,
        height: float,
        current: float,
        width: float,
        tip_magnetization: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        xreal = field.xreal

        # Spatial grid centred on the field: current line sits at x = 0.
        # Matches Gwyddion convention: x = j * xreal / xres - xreal / 2
        x = np.linspace(0, xreal, xres, endpoint=False) - xreal / 2.0

        # Pre-computed constants (following Gwyddion mfm.c notation)
        m = current / (2.0 * np.pi * width)   # I / (2 pi w)
        w2 = 0.5 * width                      # half-width
        hh = height * height                   # h^2

        xpw2 = x + w2          # x + w/2
        xmw2 = x - w2          # x - w/2
        xpw2h2 = xpw2**2 + hh  # (x + w/2)^2 + h^2
        xmw2h2 = xmw2**2 + hh  # (x - w/2)^2 + h^2

        # --- Hx (1-D) ---
        # Gwyddion: m * atan(h * w / (h^2 + x^2 - w2^2))
        # Equivalent to (I / (2 pi w)) * [atan((x+w/2)/h) - atan((x-w/2)/h)]
        hx_1d = m * np.arctan2(height * width, hh + x**2 - w2**2)

        # --- Hz (1-D) ---
        # Gwyddion: 0.5 * m * ln((x-w/2)^2 + h^2) / ((x+w/2)^2 + h^2))
        hz_1d = 0.5 * m * np.log(xmw2h2 / xpw2h2)

        # --- dHz/dz (1-D), analytical derivative ---
        # Gwyddion: m * x * h * w / ((xmw2h2) * (xpw2h2))
        t = 1.0 / (xmw2h2 * xpw2h2)
        dhz_dz_1d = m * x * height * width * t

        # Tile 1-D rows into 2-D arrays (field is constant along y).
        hx_2d = np.tile(hx_1d, (yres, 1))
        hz_2d = np.tile(hz_1d, (yres, 1))

        # Force on a point-dipole tip: Fz = mu_0 * m_tip * dHz/dz
        fz_1d = MU_0 * tip_magnetization * dhz_dz_1d
        fz_2d = np.tile(fz_1d, (yres, 1))

        return (
            field.replace(data=hx_2d, si_unit_z="A/m"),
            field.replace(data=hz_2d, si_unit_z="A/m"),
            field.replace(data=fz_2d, si_unit_z="N"),
        )
