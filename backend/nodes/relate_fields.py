"""Relate two fields — fit functional relationships between two data fields."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Relate Fields")
class RelateFields:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field_a": ("DATA_FIELD",),
                "field_b": ("DATA_FIELD",),
                "function": (["linear", "quadratic", "cubic", "power", "logarithmic"],
                             {"default": "linear"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'predicted'),
        ('RECORD_TABLE', 'fit_params'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit a functional relationship between two data fields: b = f(a). "
        "Outputs the predicted field_b from the fit and a table of fitted "
        "parameters with R² goodness-of-fit. "
    )

    KEYWORDS = ("fit", "regression", "correlate", "polynomial", "power", "logarithmic")

    def process(self, field_a: DataField, field_b: DataField,
                function: str) -> tuple:
        a = np.asarray(field_a.data, dtype=np.float64).ravel()
        b = np.asarray(field_b.data, dtype=np.float64).ravel()
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]

        records = RecordTable()

        if function == "linear":
            coeffs = np.polyfit(a, b, 1)
            predicted = np.polyval(coeffs, a)
            records.append({"quantity": "slope", "value": f"{coeffs[0]:.6g}", "unit": ""})
            records.append({"quantity": "intercept", "value": f"{coeffs[1]:.6g}", "unit": ""})

        elif function == "quadratic":
            coeffs = np.polyfit(a, b, 2)
            predicted = np.polyval(coeffs, a)
            for i, name in enumerate(["a2", "a1", "a0"]):
                records.append({"quantity": name, "value": f"{coeffs[i]:.6g}", "unit": ""})

        elif function == "cubic":
            coeffs = np.polyfit(a, b, 3)
            predicted = np.polyval(coeffs, a)
            for i, name in enumerate(["a3", "a2", "a1", "a0"]):
                records.append({"quantity": name, "value": f"{coeffs[i]:.6g}", "unit": ""})

        elif function == "power":
            # b = c * a^n  →  log(b) = log(c) + n*log(a)
            valid = (a > 0) & (b > 0)
            if valid.sum() < 2:
                predicted = np.zeros_like(a)
                records.append({"quantity": "error", "value": "insufficient positive values", "unit": ""})
            else:
                log_coeffs = np.polyfit(np.log(a[valid]), np.log(b[valid]), 1)
                n_exp = log_coeffs[0]
                c = np.exp(log_coeffs[1])
                predicted = np.where(a > 0, c * np.power(a, n_exp), 0)
                records.append({"quantity": "exponent", "value": f"{n_exp:.6g}", "unit": ""})
                records.append({"quantity": "coefficient", "value": f"{c:.6g}", "unit": ""})

        elif function == "logarithmic":
            # b = a0 + a1 * log(a)
            valid = a > 0
            if valid.sum() < 2:
                predicted = np.zeros_like(a)
                records.append({"quantity": "error", "value": "insufficient positive values", "unit": ""})
            else:
                coeffs = np.polyfit(np.log(a[valid]), b[valid], 1)
                predicted = np.where(a > 0, np.polyval(coeffs, np.log(a)), 0)
                records.append({"quantity": "log_coeff", "value": f"{coeffs[0]:.6g}", "unit": ""})
                records.append({"quantity": "intercept", "value": f"{coeffs[1]:.6g}", "unit": ""})
        else:
            predicted = np.zeros_like(a)

        # R² statistic
        ss_res = np.sum((b - predicted)**2)
        ss_tot = np.sum((b - b.mean())**2)
        r2 = 1.0 - ss_res / max(ss_tot, 1e-30)
        records.append({"quantity": "R²", "value": f"{r2:.6f}", "unit": ""})

        pred_field = field_b.replace(data=predicted.reshape(field_b.data.shape))
        return (pred_field, records)
