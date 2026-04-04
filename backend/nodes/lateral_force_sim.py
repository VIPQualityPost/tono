"""Lateral Force Simulation — topography artifacts in friction channels."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Lateral Force Simulation")
class LateralForceSim:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "direction": (["forward", "reverse", "both"],),
                "friction_coefficient": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 10.0, "step": 0.01,
                }),
                "adhesion": ("FLOAT", {
                    "default": 1e-9, "min": 0.0, "max": 1e-6, "step": 1e-12,
                }),
                "load": ("FLOAT", {
                    "default": 10e-9, "min": 1e-12, "max": 1e-6, "step": 1e-12,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'forward'),
        ('DATA_FIELD', 'reverse'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Simulates topography-induced artifacts in lateral force (friction) "
        "microscopy channels. Computes the lateral force signal from surface "
        "slope, friction coefficient, adhesion, and normal load for forward "
        "and/or reverse scan directions. Based on a contact-mechanics model "
        "where the measured lateral force depends on the local tilt angle of "
        "the sample surface."
    )

    def process(
        self,
        field: DataField,
        direction: str,
        friction_coefficient: float,
        adhesion: float,
        load: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Surface slope angle from x-gradient of topography
        dz_dx = np.gradient(data, axis=1)
        theta = np.arctan2(dz_dx, field.dx)

        sin_theta = np.sin(theta)
        cos_theta = np.cos(theta)

        va = load * sin_theta
        vc = cos_theta
        vb = friction_coefficient * (load * vc + adhesion)
        vd = friction_coefficient * sin_theta

        # Forward scan (tip moves in +x)
        denom_fwd = vc - vd
        safe_fwd = np.abs(denom_fwd) >= 1e-30
        lateral_forward = np.where(safe_fwd, (va + vb) / np.where(safe_fwd, denom_fwd, 1.0), 0.0)

        # Reverse scan (tip moves in -x)
        denom_rev = vc + vd
        safe_rev = np.abs(denom_rev) >= 1e-30
        lateral_reverse = np.where(safe_rev, -(va - vb) / np.where(safe_rev, denom_rev, 1.0), 0.0)

        if direction == "forward":
            lateral_reverse = lateral_forward.copy()
        elif direction == "reverse":
            lateral_forward = lateral_reverse.copy()

        out_fwd = field.replace(data=lateral_forward, si_unit_z="N")
        out_rev = field.replace(data=lateral_reverse, si_unit_z="N")

        return (out_fwd, out_rev)
