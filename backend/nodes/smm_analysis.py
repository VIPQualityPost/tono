"""SMM analysis — scanning microwave microscopy 3-point calibration."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="SMM Analysis")
class SMMAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "s11_amplitude": ("DATA_FIELD",),
                "s11_phase": ("DATA_FIELD",),
                "frequency": ("FLOAT", {
                    "default": 1e9, "min": 1e6, "max": 100e9, "step": 1e6,
                }),
                "ref_impedance": ("FLOAT", {
                    "default": 50.0, "min": 1.0, "max": 1000.0,
                }),
                "cal_c1": ("FLOAT", {
                    "default": 1e-15, "min": 1e-18, "max": 1e-9, "step": 1e-18,
                }),
                "cal_c2": ("FLOAT", {
                    "default": 10e-15, "min": 1e-18, "max": 1e-9, "step": 1e-18,
                }),
                "cal_c3": ("FLOAT", {
                    "default": 100e-15, "min": 1e-18, "max": 1e-9, "step": 1e-18,
                }),
                "cal_s11_1": ("FLOAT", {
                    "default": 0.9, "min": -1.0, "max": 1.0, "step": 0.001,
                }),
                "cal_s11_2": ("FLOAT", {
                    "default": 0.5, "min": -1.0, "max": 1.0, "step": 0.001,
                }),
                "cal_s11_3": ("FLOAT", {
                    "default": 0.1, "min": -1.0, "max": 1.0, "step": 0.001,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'capacitance'),
        ('DATA_FIELD', 'impedance_real'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Scanning microwave microscopy analysis using 3-point calibration. "
        "Corrects measured S11 reflection data using three known calibration "
        "capacitances to solve for the VNA error coefficients (e00, e01, e11), "
        "then extracts tip-sample capacitance and real impedance maps."
    )

    KEYWORDS = ("microwave", "s11", "capacitance", "impedance", "vna", "calibration")

    def process(
        self,
        s11_amplitude: DataField,
        s11_phase: DataField,
        frequency: float,
        ref_impedance: float,
        cal_c1: float,
        cal_c2: float,
        cal_c3: float,
        cal_s11_1: float,
        cal_s11_2: float,
        cal_s11_3: float,
    ) -> tuple:
        omega = 2.0 * np.pi * frequency

        # --- Step 1: Compute ideal S11 for each calibration capacitance ---
        cal_caps = [cal_c1, cal_c2, cal_c3]
        cal_s11_meas = [cal_s11_1, cal_s11_2, cal_s11_3]
        s11_ideal = []
        for c in cal_caps:
            z_load = 1.0 / (1j * omega * c)
            s11_ideal.append(
                (z_load - ref_impedance) / (z_load + ref_impedance)
            )

        # --- Step 2: Solve for error coefficients (e00, e01, e11) ---
        # Model: S11m_i = e00 + e01 * S11a_i / (1 - e11 * S11a_i)
        # Rearranged: S11m_i * (1 - e11 * S11a_i) = e00 * (1 - e11 * S11a_i) + e01 * S11a_i
        # S11m_i = e00 + S11a_i * (e01 + e11 * S11m_i - e11 * e00)
        #
        # Linear form with unknowns [e00, e01, e11]:
        #   S11m_i = e00 + e01 * S11a_i / (1 - e11 * S11a_i)
        # Multiply through by (1 - e11 * S11a_i):
        #   S11m_i - S11m_i * e11 * S11a_i = e00 - e00 * e11 * S11a_i + e01 * S11a_i
        # Rearrange to a linear system in (e00, e01, e11):
        #   S11m_i = e00 + e01 * S11a_i + e11 * S11a_i * S11m_i
        # This follows because the product e00*e11 can be absorbed by defining
        # the system as: S11m = e00 + e01*Ga + e11*Ga*S11m
        # where Ga = S11_ideal.
        #
        # Matrix row: [1, S11a_i, S11a_i * S11m_i] * [e00, e01, e11]^T = S11m_i

        A = np.zeros((3, 3), dtype=complex)
        b = np.zeros(3, dtype=complex)
        for i in range(3):
            ga = s11_ideal[i]
            sm = cal_s11_meas[i]
            A[i, 0] = 1.0
            A[i, 1] = ga
            A[i, 2] = ga * sm
            b[i] = sm

        coeffs = np.linalg.solve(A, b)
        e00 = coeffs[0]
        e01 = coeffs[1]
        e11 = coeffs[2]

        # --- Step 3: Apply calibration to measured S11 data ---
        amp = np.asarray(s11_amplitude.data, dtype=np.float64)
        phase = np.asarray(s11_phase.data, dtype=np.float64)
        s11m_complex = amp * np.exp(1j * phase)

        # Invert the error model: Ga = (S11m - e00) / (e01 + e11*(S11m - e00))
        s11_corrected = (s11m_complex - e00) / (e01 + e11 * (s11m_complex - e00))

        # --- Step 4: Convert corrected S11 to impedance ---
        z_tip = ref_impedance * (1.0 + s11_corrected) / (1.0 - s11_corrected)

        # --- Step 5: Extract capacitance from admittance ---
        y_tip = 1.0 / z_tip
        capacitance = np.imag(y_tip) / omega

        impedance_real = np.real(z_tip)

        cap_field = s11_amplitude.replace(data=capacitance, si_unit_z="F")
        imp_field = s11_amplitude.replace(data=impedance_real, si_unit_z="Ohm")

        return (cap_field, imp_field)
