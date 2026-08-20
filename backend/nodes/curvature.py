from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import map_coordinates

from backend.data_types import (
    DataField,
    LineData,
    RecordTable,
    _apply_markup_overlay,
    encode_preview,
    render_datafield_preview,
)
from backend.execution_context import emit_preview, emit_table, emit_warning
from backend.node_registry import register_node
from backend.nodes.surface_common import require_compatible_xy_z_units
from backend.nodes.helpers import normalize_mask, apply_masking

_CURVATURE_COLOR = "#ff9800"
_CENTER_COLOR = "#8bd3ff"


@dataclass(frozen=True)
class _Intersection:
    t: float
    x: float
    y: float


def _canonicalize_half_pi(angle: float) -> float:
    wrapped = (float(angle) + 0.5 * np.pi) % np.pi - 0.5 * np.pi
    if wrapped <= -0.5 * np.pi + 1e-15:
        wrapped += np.pi
    return float(wrapped)


def _fit_quadratic_surface(data: np.ndarray, mask: np.ndarray | None, masking: str) -> np.ndarray | None:
    yres, xres = data.shape
    yy, xx = np.mgrid[0:yres, 0:xres]

    x = 2.0 * xx.astype(np.float64) / max(xres - 1, 1) - 1.0
    y = 2.0 * yy.astype(np.float64) / max(yres - 1, 1) - 1.0

    valid = apply_masking(data, mask, masking)

    if np.count_nonzero(valid) < 6:
        return None

    design = np.column_stack([
        np.ones(int(np.count_nonzero(valid)), dtype=np.float64),
        x[valid],
        x[valid] ** 2,
        y[valid],
        x[valid] * y[valid],
        y[valid] ** 2,
    ])
    coeffs, _, _, _ = np.linalg.lstsq(design, np.asarray(data, dtype=np.float64)[valid], rcond=None)
    return np.asarray(coeffs, dtype=np.float64)


def _curvature_at_apex(coeffs: np.ndarray) -> tuple[int, float, float, float, float, float, float, float]:
    a, bx, by, cxx, cxy, cyy = [float(value) for value in coeffs]

    if abs(cxx) + abs(cxy) + abs(cyy) <= 1e-14 * (abs(bx) + abs(by)):
        return 0, 0.0, 0.0, 0.0, float(0.5 * np.pi), 0.0, 0.0, a

    cm = cxx - cyy
    cp = cxx + cyy
    phi = 0.5 * float(np.arctan2(cxy, cm))
    radius = float(np.hypot(cm, cxy))
    cx = cp + radius
    cy = cp - radius
    cos_phi = float(np.cos(phi))
    sin_phi = float(np.sin(phi))
    bx1 = bx * cos_phi + by * sin_phi
    by1 = -bx * sin_phi + by * cos_phi

    if abs(cx) < 1e-14 * abs(cy):
        xc = 0.0
        yc = -by1 / cy
        degree = 1
    elif abs(cy) < 1e-14 * abs(cx):
        xc = -bx1 / cx
        yc = 0.0
        degree = 1
    else:
        xc = -bx1 / cx
        yc = -by1 / cy
        degree = 2

    x_center = xc * cos_phi - yc * sin_phi
    y_center = xc * sin_phi + yc * cos_phi
    z_center = a + xc * bx1 + yc * by1 + xc * xc * cx + yc * yc * cy

    if cx > cy:
        cx, cy = cy, cx
        phi += 0.5 * np.pi
    phi = -phi

    phi1 = _canonicalize_half_pi(phi)
    phi2 = _canonicalize_half_pi(phi + 0.5 * np.pi)
    return degree, float(cx), float(cy), phi1, phi2, float(x_center), float(y_center), float(z_center)


def _compute_curvature_results(
    field: DataField,
    mask: np.ndarray | None,
    masking: str,
) -> dict[str, float] | None:
    coeffs = _fit_quadratic_surface(np.asarray(field.data, dtype=np.float64), mask, masking)
    if coeffs is None:
        return None

    xres = field.xres
    yres = field.yres
    xreal = float(field.xreal)
    yreal = float(field.yreal)
    qx = 2.0 / xreal * xres / max(xres - 1.0, 1.0)
    qy = 2.0 / yreal * yres / max(yres - 1.0, 1.0)
    q = float(np.sqrt(qx * qy))
    mx = float(np.sqrt(qx / qy))
    my = float(np.sqrt(qy / qx))

    ccoeffs = np.array([
        coeffs[0],
        mx * coeffs[1],
        my * coeffs[3],
        mx * mx * coeffs[2],
        coeffs[4],
        my * my * coeffs[5],
    ], dtype=np.float64)
    degree, kappa1, kappa2, phi1, phi2, xc, yc, zc = _curvature_at_apex(ccoeffs)
    x_norm = xc * mx
    y_norm = yc * my
    zc = float(
        coeffs[0]
        + coeffs[1] * x_norm
        + coeffs[2] * x_norm * x_norm
        + coeffs[3] * y_norm
        + coeffs[4] * x_norm * y_norm
        + coeffs[5] * y_norm * y_norm
    )

    #todo: fix inf case
    r1 = float(np.inf) if abs(kappa1) <= 1e-14 else float(1.0 / (q * q * kappa1))
    r2 = float(np.inf) if abs(kappa2) <= 1e-14 else float(1.0 / (q * q * kappa2))
    x0 = float(xc / q + 0.5 * xreal + field.xoff)
    y0 = float(yc / q + 0.5 * yreal + field.yoff)

    return {
        "degree": float(degree),
        "x0": x0,
        "y0": y0,
        "z0": float(zc),
        "r1": r1,
        "r2": r2,
        "phi1": float(phi1),
        "phi2": float(phi2),
    }


def _line_intersections(
    x0: float,
    y0: float,
    phi: float,
    x_min: float,
    y_min: float,
    width: float,
    height: float,
) -> tuple[_Intersection, _Intersection] | None:
    dx = float(np.cos(phi))
    dy = float(np.sin(phi))
    points: list[_Intersection] = []
    eps = 1e-12
    x_max = x_min + width
    y_max = y_min + height

    if abs(dx) > eps:
        for x in (x_min, x_max):
            t = (x - x0) / dx
            y = y0 + t * dy
            if y_min - eps <= y <= y_max + eps:
                points.append(_Intersection(float(t), float(np.clip(x, x_min, x_max)), float(np.clip(y, y_min, y_max))))
    if abs(dy) > eps:
        for y in (y_min, y_max):
            t = (y - y0) / dy
            x = x0 + t * dx
            if x_min - eps <= x <= x_max + eps:
                points.append(_Intersection(float(t), float(np.clip(x, x_min, x_max)), float(np.clip(y, y_min, y_max))))

    unique: list[_Intersection] = []
    for point in sorted(points, key=lambda item: item.t):
        if unique and abs(point.x - unique[-1].x) < 1e-9 and abs(point.y - unique[-1].y) < 1e-9:
            continue
        unique.append(point)

    if len(unique) < 2:
        return None
    return unique[0], unique[-1]


def _profile_from_intersections(field: DataField, start: _Intersection, end: _Intersection) -> LineData:
    x_start = start.x - field.xoff
    y_start = start.y - field.yoff
    x_end = end.x - field.xoff
    y_end = end.y - field.yoff

    px1 = x_start / max(field.xreal, 1e-30) * max(field.xres - 1, 0)
    py1 = y_start / max(field.yreal, 1e-30) * max(field.yres - 1, 0)
    px2 = x_end / max(field.xreal, 1e-30) * max(field.xres - 1, 0)
    py2 = y_end / max(field.yreal, 1e-30) * max(field.yres - 1, 0)
    n_samples = max(2, int(np.ceil(np.hypot(px2 - px1, py2 - py1))))

    t = np.linspace(0.0, 1.0, n_samples, dtype=np.float64)
    coords_y = py1 + t * (py2 - py1)
    coords_x = px1 + t * (px2 - px1)
    profile = map_coordinates(field.data, [coords_y, coords_x], order=1, mode="nearest")

    axis = np.linspace(start.t, end.t, n_samples, dtype=np.float64)
    return LineData(data=np.asarray(profile, dtype=np.float64), x_axis=axis, x_unit=field.si_unit_xy, y_unit=field.si_unit_z)


def _curvature_markup(
    field: DataField,
    center_x: float,
    center_y: float,
    intersections: list[tuple[_Intersection, _Intersection]],
) -> dict[str, object]:
    shapes: list[dict[str, object]] = []
    for start, end in intersections:
        shapes.append({
            "kind": "line",
            "x1": (start.x - field.xoff) / max(field.xreal, 1e-30),
            "y1": (start.y - field.yoff) / max(field.yreal, 1e-30),
            "x2": (end.x - field.xoff) / max(field.xreal, 1e-30),
            "y2": (end.y - field.yoff) / max(field.yreal, 1e-30),
            "width": 3,
            "color": _CURVATURE_COLOR,
        })

    if np.isfinite(center_x) and np.isfinite(center_y):
        radius = 0.015
        fx = (center_x - field.xoff) / max(field.xreal, 1e-30)
        fy = (center_y - field.yoff) / max(field.yreal, 1e-30)
        shapes.append({
            "kind": "circle",
            "x1": fx - radius,
            "y1": fy - radius,
            "x2": fx + radius,
            "y2": fy + radius,
            "width": 2,
            "color": _CENTER_COLOR,
        })

    return {"kind": "markup", "shapes": shapes}


def _empty_profile(unit_xy: str, unit_z: str) -> LineData:
    return LineData(data=np.zeros(0, dtype=np.float64), x_axis=np.zeros(0, dtype=np.float64), x_unit=unit_xy, y_unit=unit_z)


@register_node(display_name="Curvature")
class Curvature:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "masking": (["ignore", "include", "exclude"], {"default": "exclude"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('ANNOTATION_SOURCE', 'output'),
        ('RECORD_TABLE', 'measurements'),
        ('LINE', 'profile_a'),
        ('LINE', 'profile_b'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Fit a quadratic surface and report the overall principal curvature radii and directions. "
        "The output annotation marks the principal cross-sections and the node "
        "also returns the two corresponding height profiles."
    )

    KEYWORDS = ("radius", "principal", "quadratic", "bow")

    def process(
        self,
        field: DataField,
        masking: str,
        mask: np.ndarray | None = None,
    ) -> tuple:
        require_compatible_xy_z_units(field, "Curvature")
        mask_array = normalize_mask(mask, field.data.shape)
        results = _compute_curvature_results(field, mask_array, masking)

        if results is None:
            emit_warning("Curvature requires at least six usable pixels for the quadratic fit.")
            table = RecordTable([])
            emit_table(table)
            emit_preview(encode_preview(render_datafield_preview(field, field.colormap)))
            empty = _empty_profile(field.si_unit_xy, field.si_unit_z)
            return (field.replace(), table, empty, empty)

        intersections: list[tuple[_Intersection, _Intersection]] = []
        warnings: list[str] = []
        for angle_key in ("phi1", "phi2"):
            hit = _line_intersections(
                results["x0"],
                results["y0"],
                -results[angle_key],
                field.xoff,
                field.yoff,
                field.xreal,
                field.yreal,
            )
            if hit is None:
                warnings.append("Principal axes are outside the image.")
            else:
                intersections.append(hit)

        profiles = []
        for pair in intersections[:2]:
            profiles.append(_profile_from_intersections(field, pair[0], pair[1]))
        while len(profiles) < 2:
            profiles.append(_empty_profile(field.si_unit_xy, field.si_unit_z))

        markup_spec = _curvature_markup(field, results["x0"], results["y0"], intersections)
        output = field.replace(overlays=[*field.overlays, markup_spec])

        table = RecordTable([
            {"quantity": "Curvature radius 1",  "value": results["r1"],     "unit": field.si_unit_xy},
            {"quantity": "Curvature radius 2",  "value": results["r2"],     "unit": field.si_unit_xy},
            {"quantity": "Center x position",   "value": results["x0"],     "unit": field.si_unit_xy},
            {"quantity": "Center y position",   "value": results["y0"],     "unit": field.si_unit_xy},
            {"quantity": "Center value",        "value": results["z0"],     "unit": field.si_unit_z},
            {"quantity": "Direction 1",         "value": float(np.degrees(results["phi1"])), "unit": "deg"},
            {"quantity": "Direction 2",         "value": float(np.degrees(results["phi2"])), "unit": "deg"},
        ])

        preview_base = render_datafield_preview(field, field.colormap)
        panels = []

        for p, title in zip(profiles, ["Principal Axis A", "Principal Axis B"]):
            if len(p.data) > 0:
                panels.append({
                    "title": title,
                    "kind": "line_plot",
                    "line": p.data.tolist(),
                    "x_axis": p.x_axis.tolist(),
                    "x_unit": field.si_unit_xy,
                })
        panels.append({
            "title": "Overview",
            "kind": "image",
            "image": encode_preview(_apply_markup_overlay(preview_base, field, markup_spec)),
        })

        emit_preview({"kind": "panels", "panels": panels})
        emit_table(table)

        if warnings:
            emit_warning(warnings[0])

        return (output, table, profiles[0], profiles[1])
