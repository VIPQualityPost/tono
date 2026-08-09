"""Straighten path — extract cross-section along a curved spline path."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates

from backend.node_registry import register_node
from backend.data_types import DataField, LineData, datafield_to_uint8, encode_preview
from backend.execution_context import emit_overlay, emit_value
from backend.nodes.helpers import _scalar_payload


@register_node(display_name="Straighten Path")
class StraightenPath:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "points_x": ("STRING", {"default": "0.25, 0.5, 0.75", "hidden": True}),
                "points_y": ("STRING", {"default": "0.5, 0.3, 0.5", "hidden": True}),
                "thickness": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
                "n_samples": ("INT", {"default": 256, "min": 10, "max": 2048, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'straightened'),
        ('LINE', 'profile'),
        ('FLOAT', 'length'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract a cross-section along an arbitrary curved path defined by "
        "control points. The path is a natural cubic spline through the "
        "points. Drag the points on the preview to reshape the path; the "
        "shaded band shows the sampling thickness. The physical path length "
        "is reported alongside the straightened strip. "
    )

    KEYWORDS = ("unbend", "unroll", "spline", "curved profile", "extract path")

    def process(self, field: DataField, points_x: str, points_y: str,
                thickness: int, n_samples: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        fx = [float(v.strip()) for v in points_x.split(",") if v.strip()]
        fy = [float(v.strip()) for v in points_y.split(",") if v.strip()]
        n_pts = min(len(fx), len(fy))
        fx, fy = fx[:n_pts], fy[:n_pts]

        emit_overlay({
            "kind": "straighten_path",
            "section_title": "Path",
            "image": encode_preview(datafield_to_uint8(field, field.colormap)),
            "points": [{"x": float(fx[i]), "y": float(fy[i])} for i in range(n_pts)],
            "thickness": int(thickness),
            "xres": int(xres),
            "yres": int(yres),
        })

        if n_pts < 2:
            empty_line = LineData(
                data=np.zeros(0, dtype=np.float64),
                x_axis=np.zeros(0, dtype=np.float64),
                x_unit=field.si_unit_xy,
                y_unit=field.si_unit_z,
            )
            emit_value(_scalar_payload(0.0, field.si_unit_xy))
            return (field, empty_line, 0.0)

        px = [f * (xres - 1) for f in fx]
        py = [f * (yres - 1) for f in fy]

        t_ctrl = np.linspace(0, 1, n_pts)
        t_sample = np.linspace(0, 1, n_samples)
        if n_pts >= 3:
            cx = CubicSpline(t_ctrl, px, bc_type="natural")(t_sample)
            cy = CubicSpline(t_ctrl, py, bc_type="natural")(t_sample)
        else:
            cx = np.interp(t_sample, t_ctrl, px)
            cy = np.interp(t_sample, t_ctrl, py)

        if thickness <= 1:
            values = map_coordinates(data, [cy, cx], order=1, mode='nearest')
            result = values.reshape(1, -1)
        else:
            dcx = np.gradient(cx)
            dcy = np.gradient(cy)
            length = np.sqrt(dcx**2 + dcy**2)
            length = np.maximum(length, 1e-10)
            nx = -dcy / length
            ny = dcx / length

            offsets = np.linspace(-(thickness - 1) / 2, (thickness - 1) / 2, thickness)
            result = np.zeros((thickness, n_samples))
            for i, off in enumerate(offsets):
                sx = cx + off * nx
                sy = cy + off * ny
                result[i] = map_coordinates(data, [sy, sx], order=1, mode='nearest')

        total_length = 0.0
        for i in range(1, len(cx)):
            dx_phys = (cx[i] - cx[i - 1]) * field.dx
            dy_phys = (cy[i] - cy[i - 1]) * field.dy
            total_length += np.sqrt(dx_phys**2 + dy_phys**2)

        center_values = map_coordinates(data, [cy, cx], order=1, mode='nearest')
        profile = LineData(
            data=center_values,
            x_axis=np.linspace(0.0, total_length, n_samples),
            x_unit=field.si_unit_xy,
            y_unit=field.si_unit_z,
        )

        straightened = field.replace(
            data=result, xreal=total_length,
            yreal=thickness * max(field.dx, field.dy),
        )
        emit_value(_scalar_payload(float(total_length), field.si_unit_xy))
        return (straightened, profile, float(total_length))
