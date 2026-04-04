"""PFM analysis — piezoresponse force microscopy polarization vectors."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="PFM Analysis")
class PFMAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vpfm_amplitude": ("DATA_FIELD",),
                "lpfm_amplitude": ("DATA_FIELD",),
                "vpfm_phase": ("DATA_FIELD",),
                "lpfm_phase": ("DATA_FIELD",),
                "mode": (["2d", "3d"],),
                "lateral_sensitivity": ("FLOAT", {
                    "default": 1.0, "min": 0.01, "max": 100.0, "step": 0.01,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'magnitude'),
        ('DATA_FIELD', 'azimuth'),
        ('DATA_FIELD', 'inclination'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Piezoresponse force microscopy analysis. Computes in-plane (2D) or "
        "full 3D polarization vectors from vertical and lateral PFM amplitude "
        "and phase channels. The lateral sensitivity parameter scales the "
        "lateral signal relative to the vertical. Outputs are the polarization "
        "magnitude, the in-plane azimuth angle, and the out-of-plane "
        "inclination angle (zero in 2D mode)."
    )

    def process(
        self,
        vpfm_amplitude: DataField,
        lpfm_amplitude: DataField,
        vpfm_phase: DataField,
        lpfm_phase: DataField,
        mode: str,
        lateral_sensitivity: float,
    ) -> tuple:
        va = np.asarray(vpfm_amplitude.data, dtype=np.float64)
        la = np.asarray(lpfm_amplitude.data, dtype=np.float64)
        vp = np.asarray(vpfm_phase.data, dtype=np.float64)
        lp = np.asarray(lpfm_phase.data, dtype=np.float64)

        # In-plane components from lateral PFM
        x = la * lateral_sensitivity * np.cos(lp)
        y = la * lateral_sensitivity * np.sin(lp)
        # Out-of-plane component from vertical PFM
        z = va * np.cos(vp)

        xy_mag = np.sqrt(x**2 + y**2)
        azimuth = np.arctan2(y, x)

        if mode == "2d":
            magnitude = xy_mag
            inclination = np.zeros_like(magnitude)
        else:
            magnitude = np.sqrt(x**2 + y**2 + z**2)
            inclination = np.arctan2(z, xy_mag)

        return (
            vpfm_amplitude.replace(data=magnitude, si_unit_z=""),
            vpfm_amplitude.replace(data=azimuth, si_unit_z="rad"),
            vpfm_amplitude.replace(data=inclination, si_unit_z="rad"),
        )
