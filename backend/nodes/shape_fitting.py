"""Shape fitting — fit geometric primitives to surface data."""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


def _fit_sphere(x, y, z):
    """Fit z = z0 - sqrt(R² - (x-cx)² - (y-cy)²) via least squares."""
    cx0 = x.mean()
    cy0 = y.mean()
    r0 = max(x.max() - x.min(), y.max() - y.min()) * 2

    def residuals(params):
        cx, cy, z0, R = params
        r2 = (x - cx)**2 + (y - cy)**2
        valid = r2 < R**2
        model = np.where(valid, z0 - np.sqrt(np.maximum(R**2 - r2, 0)), z0)
        return z - model

    result = least_squares(residuals, [cx0, cy0, z.max(), r0], method="lm")
    cx, cy, z0, R = result.x
    return {"cx": cx, "cy": cy, "z0": z0, "R": abs(R)}, result.fun


def _fit_paraboloid(x, y, z):
    """Fit z = z0 + a*(x-cx)² + b*(y-cy)² via least squares."""
    cx0 = x.mean()
    cy0 = y.mean()

    def residuals(params):
        cx, cy, z0, a, b = params
        model = z0 + a * (x - cx)**2 + b * (y - cy)**2
        return z - model

    result = least_squares(residuals, [cx0, cy0, z.mean(), 0.0, 0.0], method="lm")
    cx, cy, z0, a, b = result.x
    return {"cx": cx, "cy": cy, "z0": z0, "a": a, "b": b}, result.fun


def _fit_cylinder(x, y, z):
    """Fit z = z0 + a*(x*cos(θ) + y*sin(θ) - d)² (cylinder along one axis)."""
    def residuals(params):
        z0, a, theta, d = params
        u = x * np.cos(theta) + y * np.sin(theta) - d
        model = z0 + a * u**2
        return z - model

    result = least_squares(residuals, [z.mean(), 0.0, 0.0, 0.0], method="lm")
    z0, a, theta, d = result.x
    R = abs(0.5 / a) if abs(a) > 1e-20 else float("inf")
    return {"z0": z0, "curvature": a, "angle_deg": np.degrees(theta), "R": R}, result.fun


@register_node(display_name="Shape Fitting")
class ShapeFitting:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shape": (["sphere", "paraboloid", "cylinder"], {"default": "sphere"}),
                "output": (["residual", "fitted"], {"default": "residual"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
        ('RECORD_TABLE', 'parameters'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit a geometric primitive (sphere, paraboloid, or cylinder) to the "
        "surface data. Outputs either the fitted surface or the residual "
        "(original minus fit). Reports fitted parameters including radius "
        "of curvature, centre position, etc. "
        "Equivalent to Gwyddion's fit-shape.c module."
    )

    def process(self, field: DataField, shape: str, output: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        # Build physical coordinate grids
        x = np.arange(xres) * field.dx + field.xoff
        y = np.arange(yres) * field.dy + field.yoff
        X, Y = np.meshgrid(x, y)
        x_flat = X.ravel()
        y_flat = Y.ravel()
        z_flat = data.ravel()

        if shape == "sphere":
            params, residuals = _fit_sphere(x_flat, y_flat, z_flat)
        elif shape == "paraboloid":
            params, residuals = _fit_paraboloid(x_flat, y_flat, z_flat)
        elif shape == "cylinder":
            params, residuals = _fit_cylinder(x_flat, y_flat, z_flat)
        else:
            raise ValueError(f"Unknown shape: {shape!r}")

        # Reconstruct the fitted surface
        residual_map = residuals.reshape(data.shape)
        fitted_map = data - residual_map

        if output == "residual":
            out_data = residual_map
        else:
            out_data = fitted_map

        # Build result table
        records: RecordTable = RecordTable()
        rms = float(np.sqrt(np.mean(residuals**2)))
        records.append({"quantity": "RMS residual", "value": f"{rms:.4g}", "unit": field.si_unit_z})

        unit_xy = field.si_unit_xy
        unit_z = field.si_unit_z
        for key, val in params.items():
            if key in ("cx", "cy", "R", "d"):
                records.append({"quantity": key, "value": f"{val:.4g}", "unit": unit_xy})
            elif key in ("z0",):
                records.append({"quantity": key, "value": f"{val:.4g}", "unit": unit_z})
            elif key == "angle_deg":
                records.append({"quantity": "angle", "value": f"{val:.2f}", "unit": "deg"})
            else:
                records.append({"quantity": key, "value": f"{val:.4g}", "unit": ""})

        return (field.replace(data=out_data), records)
