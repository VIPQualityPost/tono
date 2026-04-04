from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import map_coordinates

from backend.data_types import LineData, RecordTable
from backend.execution_context import emit_overlay, emit_table, emit_warning
from backend.node_registry import register_node
from backend.nodes.spectral_common import _window_vector


_LOG_TINY = float(np.finfo(np.float64).tiny)


@dataclass(frozen=True)
class _FractalMethod:
    display_name: str
    x_label: str
    y_label: str


_METHODS: dict[str, _FractalMethod] = {
    "partitioning": _FractalMethod("Partitioning", "log h", "log S"),
    "cube_counting": _FractalMethod("Cube counting", "log h", "log N"),
    "triangulation": _FractalMethod("Triangulation", "log h", "log A"),
    "psdf": _FractalMethod("Power spectrum", "log k", "log W"),
    "hhcf": _FractalMethod("Structure function", "log h", "log H"),
}


def _clamp01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _resample_square(data: np.ndarray, size: int, interpolation: str) -> np.ndarray:
    source = np.asarray(data, dtype=np.float64)
    if source.shape == (size, size):
        return source.copy()

    order_map = {"nearest": 0, "linear": 1, "cubic": 3}
    if interpolation not in order_map:
        raise ValueError(f"Unknown interpolation mode: {interpolation}")

    yres, xres = source.shape
    yy, xx = np.meshgrid(
        np.linspace(0.0, max(yres - 1, 0), size, dtype=np.float64),
        np.linspace(0.0, max(xres - 1, 0), size, dtype=np.float64),
        indexing="ij",
    )
    return np.asarray(
        map_coordinates(
            source,
            [yy, xx],
            order=order_map[interpolation],
            mode="nearest",
            prefilter=order_map[interpolation] > 1,
        ),
        dtype=np.float64,
    )


def _safe_log(values: np.ndarray | float) -> np.ndarray | float:
    return np.log(np.clip(values, _LOG_TINY, None))


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    coeffs = np.polyfit(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), 1)
    return float(coeffs[0]), float(coeffs[1])


def _row_level2(row: np.ndarray) -> np.ndarray:
    values = np.asarray(row, dtype=np.float64)
    if values.size <= 1:
        return values.copy()
    x = np.linspace(-1.0, 1.0, values.size, dtype=np.float64)
    A = np.column_stack((np.ones_like(x), x))
    coeffs, _, _, _ = np.linalg.lstsq(A, values, rcond=None)
    return values - (coeffs[0] + coeffs[1] * x)


def _window_with_rms_compensation(values: np.ndarray, window: np.ndarray) -> np.ndarray:
    row = np.asarray(values, dtype=np.float64)
    rms = float(np.sqrt(np.mean(row * row)))
    weighted = row * window
    new_rms = float(np.sqrt(np.mean(weighted * weighted)))
    if rms > 0.0 and new_rms > 0.0:
        weighted *= rms / new_rms
    return weighted


def _fractal_partitioning(data: np.ndarray, interpolation: str) -> tuple[np.ndarray, np.ndarray]:
    xres = int(data.shape[1])
    dimexp = int(np.floor(np.log(float(max(xres, 2))) / np.log(2.0) + 0.5))
    if dimexp < 2:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    size = (1 << dimexp) + 1
    buffer = _resample_square(data, size, interpolation)
    xvals = np.empty(dimexp - 1, dtype=np.float64)
    yvals = np.empty(dimexp - 1, dtype=np.float64)

    for l in range(1, dimexp):
        rp = 1 << l
        nx = (size - 1) // rp - 1
        ny = (size - 1) // rp - 1
        accum = 0.0
        for i in range(nx):
            for j in range(ny):
                block = buffer[j * rp:j * rp + rp, i * rp:i * rp + rp]
                rms = float(np.std(block, ddof=0))
                accum += rms * rms
        xvals[l - 1] = np.log(float(rp))
        denom = max(nx * ny, 1)
        yvals[l - 1] = float(_safe_log(accum / denom))

    return xvals, yvals


def _fractal_cube_counting(data: np.ndarray, interpolation: str) -> tuple[np.ndarray, np.ndarray]:
    xres = int(data.shape[1])
    dimexp = int(np.floor(np.log(float(max(xres, 2))) / np.log(2.0) + 0.5))
    if dimexp < 1:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    size = (1 << dimexp) + 1
    buffer = _resample_square(data, size, interpolation)
    imin = float(np.min(buffer))
    height = float(np.max(buffer) - imin)
    if not np.isfinite(height) or height <= 0.0:
        height = _LOG_TINY

    xvals = np.empty(dimexp, dtype=np.float64)
    yvals = np.empty(dimexp, dtype=np.float64)

    for l in range(dimexp):
        rp = 1 << (l + 1)
        rp2 = (1 << dimexp) // rp
        a = max(height / rp, _LOG_TINY)
        accum = 0.0
        for i in range(rp):
            for j in range(rp):
                block = buffer[j * rp2:j * rp2 + rp2 + 1, i * rp2:i * rp2 + rp2 + 1] - imin
                maxv = float(np.max(block))
                minv = float(np.min(block))
                accum += rp - np.floor(minv / a) - np.floor((height - maxv) / a)
        xvals[l] = float((l + 1 - dimexp) * np.log(2.0))
        yvals[l] = float(_safe_log(accum))

    return xvals, yvals


def _fractal_triangulation(data: np.ndarray, interpolation: str) -> tuple[np.ndarray, np.ndarray]:
    xres = int(data.shape[1])
    dimexp = int(np.floor(np.log(float(max(xres, 2))) / np.log(2.0) + 0.5))
    if dimexp < 0:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    size = (1 << dimexp) + 1
    buffer = _resample_square(data, size, interpolation)
    height = float(np.max(buffer) - np.min(buffer))
    if not np.isfinite(height) or height <= 0.0:
        height = _LOG_TINY
    dil = float((1 << dimexp) / height)
    dil *= dil

    xvals = np.empty(dimexp + 1, dtype=np.float64)
    yvals = np.empty(dimexp + 1, dtype=np.float64)

    for l in range(dimexp + 1):
        rp = 1 << l
        rp2 = (1 << dimexp) // rp
        accum = 0.0
        for i in range(rp):
            for j in range(rp):
                z1 = float(buffer[j * rp2, i * rp2])
                z2 = float(buffer[j * rp2, (i + 1) * rp2])
                z3 = float(buffer[(j + 1) * rp2, i * rp2])
                z4 = float(buffer[(j + 1) * rp2, (i + 1) * rp2])

                a = float(np.sqrt(rp2 * rp2 + dil * (z1 - z2) * (z1 - z2)))
                b = float(np.sqrt(rp2 * rp2 + dil * (z1 - z3) * (z1 - z3)))
                c = float(np.sqrt(rp2 * rp2 + dil * (z3 - z4) * (z3 - z4)))
                d = float(np.sqrt(rp2 * rp2 + dil * (z2 - z4) * (z2 - z4)))
                e = float(np.sqrt(2.0 * rp2 * rp2 + dil * (z3 - z2) * (z3 - z2)))

                s1 = 0.5 * (a + b + e)
                s2 = 0.5 * (c + d + e)
                term1 = max(s1 * (s1 - a) * (s1 - b) * (s1 - e), 0.0)
                term2 = max(s2 * (s2 - c) * (s2 - d) * (s2 - e), 0.0)
                accum += np.sqrt(term1) + np.sqrt(term2)
        xvals[l] = float((l - dimexp) * np.log(2.0))
        yvals[l] = float(_safe_log(accum))

    return xvals, yvals


def _fractal_psdf(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows, width = data.shape
    if width < 2 or rows < 1:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    window = _window_vector(width, "hann")
    accum = np.zeros(width // 2 + 1, dtype=np.float64)
    for row in np.asarray(data, dtype=np.float64):
        leveled = _row_level2(row)
        weighted = _window_with_rms_compensation(leveled, window)
        spectrum = np.fft.rfft(weighted)
        accum += np.abs(spectrum) ** 2
    accum /= float(rows)

    indices = np.arange(1, accum.size, dtype=np.float64)
    return np.log(indices), _safe_log(accum[1:])


def _fractal_hhcf(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows, width = data.shape
    if width < 2 or rows < 1:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    accum = np.zeros(width, dtype=np.float64)
    for row in np.asarray(data, dtype=np.float64):
        leveled = _row_level2(row)
        for lag in range(width):
            if lag == 0:
                accum[lag] += 0.0
            else:
                diffs = leveled[lag:] - leveled[:-lag]
                accum[lag] += float(np.mean(diffs * diffs)) if diffs.size else 0.0
    accum /= float(rows)

    outres = min(width - 1, (width + 5) // 10 + int(np.rint(np.sqrt(width))))
    indices = np.arange(1, outres + 1, dtype=np.float64)
    return np.log(indices), _safe_log(accum[1:outres + 1])


def _compute_method(field_data: np.ndarray, method: str, interpolation: str) -> tuple[np.ndarray, np.ndarray]:
    if method == "partitioning":
        return _fractal_partitioning(field_data, interpolation)
    if method == "cube_counting":
        return _fractal_cube_counting(field_data, interpolation)
    if method == "triangulation":
        return _fractal_triangulation(field_data, interpolation)
    if method == "psdf":
        return _fractal_psdf(field_data)
    if method == "hhcf":
        return _fractal_hhcf(field_data)
    raise ValueError(f"Unknown fractal method: {method}")


def _dimension_from_slope(method: str, slope: float) -> float:
    if method == "partitioning":
        return 3.0 - slope / 2.0
    if method == "cube_counting":
        return slope
    if method == "triangulation":
        return 2.0 + slope
    if method == "psdf":
        return 3.5 + slope / 2.0
    if method == "hhcf":
        return 3.0 - slope / 2.0
    raise ValueError(f"Unknown fractal method: {method}")


def _select_fit_range(xvals: np.ndarray, x1: float, x2: float) -> tuple[np.ndarray, float, float]:
    if xvals.size == 0:
        return np.zeros(0, dtype=bool), 0.0, 0.0

    xmin = float(np.min(xvals))
    xmax = float(np.max(xvals))
    if abs(float(x1) - float(x2)) < 1e-9:
        return np.ones(xvals.size, dtype=bool), xmin, xmax

    lo_frac = min(float(x1), float(x2))
    hi_frac = max(float(x1), float(x2))
    lo = xmin + lo_frac * (xmax - xmin)
    hi = xmin + hi_frac * (xmax - xmin)
    mask = (xvals >= lo) & (xvals <= hi)
    return mask, float(lo), float(hi)


@register_node(display_name="Fractal Dimension")
class FractalDimension:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (list(_METHODS.keys()), {"default": "partitioning"}),
                "interpolation": (["linear", "nearest", "cubic"], {"default": "linear"}),
                "x1": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            }
        }

    OUTPUTS = (
        ('FLOAT', 'dimension'),
        ('LINE', 'curve'),
        ('RECORD_TABLE', 'measurements'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Calculate the surface fractal dimension using Gwyddion's partitioning, cube counting, triangulation, "
        "power-spectrum, or HHCF methods. The in-node graph shows the log-log curve and lets you drag the fit range."
    )

    KEYWORDS = ("partitioning", "cube counting", "triangulation", "hhcf", "box counting", "self similar")

    def process(
        self,
        field,
        method: str,
        interpolation: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> tuple:
        xvals, yvals = _compute_method(np.asarray(field.data, dtype=np.float64), method, interpolation)
        finite = np.isfinite(xvals) & np.isfinite(yvals)
        xvals = np.asarray(xvals[finite], dtype=np.float64)
        yvals = np.asarray(yvals[finite], dtype=np.float64)

        line = LineData(data=yvals, x_axis=xvals, x_unit="", y_unit="")

        x1 = _clamp01(x1)
        x2 = _clamp01(x2)
        y1 = _clamp01(y1)
        y2 = _clamp01(y2)

        fit_mask, fit_from, fit_to = _select_fit_range(xvals, x1, x2)
        if np.count_nonzero(fit_mask) >= 2:
            slope, intercept = _fit_line(xvals[fit_mask], yvals[fit_mask])
            dimension = _dimension_from_slope(method, slope)
        else:
            slope = float("nan")
            intercept = float("nan")
            dimension = float("nan")
            emit_warning("Fractal fit range contains fewer than two usable points.")

        table = RecordTable([
            {"quantity": "Dimension", "value": float(dimension), "unit": ""},
            {"quantity": "Fit slope", "value": float(slope), "unit": ""},
            {"quantity": "Fit intercept", "value": float(intercept), "unit": ""},
            {"quantity": "Fit from", "value": float(fit_from), "unit": ""},
            {"quantity": "Fit to", "value": float(fit_to), "unit": ""},
        ])

        method_info = _METHODS[method]
        emit_overlay({
            "kind": "line_plot",
            "section_title": "Fractal Dimension",
            "line": yvals.tolist(),
            "x_axis": xvals.tolist(),
            "x_label": method_info.x_label,
            "y_label": method_info.y_label,
            "x1": x1,
            "x2": x2,
            "y1": y1,
            "y2": y2,
            "a_locked": False,
            "b_locked": False,
        })
        emit_table(table)

        return (float(dimension), line, table)
