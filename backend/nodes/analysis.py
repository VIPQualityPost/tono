"""
Analysis nodes — statistics, histograms, FFT, cross sections.

Gwyddion equivalents:
  StatisticsNode  → gwy_data_field_get_min/max/avg/rms (libprocess/stats.h)
  HeightHistogram → DH (height distribution), gwy_data_field_dh
  FFT2D           → gwy_data_field_2dfft + gwy_data_field_2dpsdf
  CrossSection    → gwy_data_field_get_profile (libprocess/datafield.c)
"""

from __future__ import annotations
import numpy as np
from typing import Callable
from backend.node_registry import register_node
from backend.data_types import DataField, MeasureTable, RecordTable, datafield_to_uint8, encode_preview


# ---------------------------------------------------------------------------
# StatisticsNode
# ---------------------------------------------------------------------------

@register_node(display_name="Statistics")
class StatisticsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ("MEASURE_TABLE",)
    RETURN_NAMES = ("stats",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute basic surface statistics: min, max, mean, RMS roughness, median, "
        "and skewness. Equivalent to gwy_data_field_get_min/max/avg/rms."
    )

    def process(self, field: DataField) -> tuple:
        d = field.data
        mean = float(d.mean())
        rms = float(np.sqrt(np.mean((d - mean) ** 2)))
        skewness = float(np.mean(((d - mean) / rms) ** 3)) if rms > 0 else 0.0
        kurtosis = float(np.mean(((d - mean) / rms) ** 4)) if rms > 0 else 0.0

        table = MeasureTable([
            {"quantity": "min",      "value": float(d.min()),    "unit": field.si_unit_z},
            {"quantity": "max",      "value": float(d.max()),    "unit": field.si_unit_z},
            {"quantity": "mean",     "value": mean,              "unit": field.si_unit_z},
            {"quantity": "RMS",      "value": rms,               "unit": field.si_unit_z},
            {"quantity": "median",   "value": float(np.median(d)), "unit": field.si_unit_z},
            {"quantity": "skewness", "value": skewness,          "unit": ""},
            {"quantity": "kurtosis", "value": kurtosis,          "unit": ""},
            {"quantity": "range",    "value": float(d.max() - d.min()), "unit": field.si_unit_z},
        ])
        return (table,)


# ---------------------------------------------------------------------------
# HeightHistogram
# ---------------------------------------------------------------------------

@register_node(display_name="Height Histogram")
class HeightHistogram:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_bins": ("INT", {"default": 256, "min": 10, "max": 1000, "step": 1}),
                "y_scale": (["linear", "log"],),
                "x1": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            }
        }

    RETURN_TYPES = ("MEASURE_TABLE",)
    RETURN_NAMES = ("measurements",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute the height distribution histogram (DH). "
        "Use log scale to reveal small peaks next to a dominant background. "
        "Outputs marker measurements while showing the histogram interactively in-node. "
        "Equivalent to gwy_data_field_dh."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self,
        field: DataField,
        n_bins: int,
        y_scale: str = "linear",
        x1: float = 0.25,
        y1: float = 0.5,
        x2: float = 0.75,
        y2: float = 0.5,
    ) -> tuple:
        raw_counts, bin_edges = np.histogram(field.data.ravel(), bins=int(n_bins))
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        counts = raw_counts.astype(np.float64)
        if y_scale == "log":
            counts = np.log10(1.0 + counts)

        x1 = float(np.clip(x1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 0.0 + 1.0))

        xmin = float(np.min(bin_centers)) if len(bin_centers) else 0.0
        xmax = float(np.max(bin_centers)) if len(bin_centers) else 1.0

        def x_frac_to_idx(frac):
            if len(bin_centers) <= 1:
                return 0
            if xmax == xmin:
                return 0
            target_x = xmin + frac * (xmax - xmin)
            return int(np.argmin(np.abs(bin_centers - target_x)))

        idx_a = x_frac_to_idx(x1)
        idx_b = x_frac_to_idx(x2)
        xa = float(bin_centers[idx_a]) if len(bin_centers) else 0.0
        xb = float(bin_centers[idx_b]) if len(bin_centers) else 0.0
        ya = float(counts[idx_a]) if len(counts) else 0.0
        yb = float(counts[idx_b]) if len(counts) else 0.0
        count_unit = "count" if y_scale == "linear" else "log10(1+count)"

        if HeightHistogram._broadcast_overlay_fn is not None:
            HeightHistogram._broadcast_overlay_fn(
                HeightHistogram._current_node_id,
                {
                    "kind": "line_plot",
                    "section_title": "Histogram",
                    "line": counts.tolist(),
                    "x_axis": bin_centers.astype(np.float64).tolist(),
                    "x1": float(np.clip(x1, 0.0, 1.0)),
                    "x2": float(np.clip(x2, 0.0, 1.0)),
                    "y1": float(y1),
                    "y2": float(y2),
                    "a_locked": False,
                    "b_locked": False,
                },
            )

        table = MeasureTable([
            {"quantity": "A position", "value": xa, "unit": field.si_unit_z},
            {"quantity": "A count",    "value": ya, "unit": count_unit},
            {"quantity": "B position", "value": xb, "unit": field.si_unit_z},
            {"quantity": "B count",    "value": yb, "unit": count_unit},
            {"quantity": "delta X",    "value": xb - xa, "unit": field.si_unit_z},
            {"quantity": "delta Y",    "value": yb - ya, "unit": count_unit},
        ])
        return (table,)


# ---------------------------------------------------------------------------
# LineCursors — interactive measurement cursors on any LINE plot
# ---------------------------------------------------------------------------

@register_node(display_name="Line Cursors")
class LineCursors:
    """Place two draggable cursors on any LINE plot to measure values and deltas."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line": ("LINE",),
                "x1": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5,  "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
            },
            "optional": {
                "x_axis": ("LINE",),
            },
        }

    RETURN_TYPES = ("MEASURE_TABLE",)
    RETURN_NAMES = ("measurement",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Place two cursors on any line plot (histogram, cross section, profile) "
        "to measure positions, values, and deltas. Drag the markers to reposition."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self, line, x1: float, y1: float, x2: float, y2: float,
        x_axis=None,
    ) -> tuple:
        y = np.asarray(line, dtype=np.float64).ravel()
        n = len(y)
        if x_axis is not None:
            x = np.asarray(x_axis, dtype=np.float64).ravel()[:n]
        else:
            x = np.arange(n, dtype=np.float64)
        x1 = float(np.clip(x1, 0.0, 1.0))
        x2 = float(np.clip(x2, 0.0, 1.0))

        xmin = float(np.min(x)) if len(x) else 0.0
        xmax = float(np.max(x)) if len(x) else 1.0

        def x_frac_to_idx(frac):
            if n <= 1:
                return 0
            if xmax == xmin:
                return 0
            target_x = xmin + frac * (xmax - xmin)
            return int(np.argmin(np.abs(x - target_x)))

        idx_a = x_frac_to_idx(x1)
        idx_b = x_frac_to_idx(x2)

        xa, ya = float(x[idx_a]), float(y[idx_a])
        xb, yb = float(x[idx_b]), float(y[idx_b])

        # --- Broadcast overlay ---
        if LineCursors._broadcast_overlay_fn is not None:
            LineCursors._broadcast_overlay_fn(
                LineCursors._current_node_id,
                {
                    "kind": "line_plot",
                    "section_title": "Line Cursors",
                    "line": y.tolist(),
                    "x_axis": x.tolist(),
                    "x1": x1,
                    "x2": x2,
                    "y1": float(y1),
                    "y2": float(y2),
                    "a_locked": False,
                    "b_locked": False,
                },
            )

        # --- Output table ---
        table = MeasureTable([
            {"quantity": "A position", "value": xa, "unit": ""},
            {"quantity": "A value",    "value": ya, "unit": ""},
            {"quantity": "B position", "value": xb, "unit": ""},
            {"quantity": "B value",    "value": yb, "unit": ""},
            {"quantity": "delta X",    "value": xb - xa, "unit": ""},
            {"quantity": "delta Y",    "value": yb - ya, "unit": ""},
        ])
        return (table,)


# ---------------------------------------------------------------------------
# FFT2D
# ---------------------------------------------------------------------------

@register_node(display_name="2D FFT")
class FFT2D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "windowing": (["hann", "hamming", "blackman", "none"],),
                "level": (["mean", "plane", "none"],),
                "output": (["log_magnitude", "magnitude", "phase", "psdf"],),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("spectrum",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute the 2D FFT with optional windowing and mean/plane subtraction. "
        "Output can be log magnitude, magnitude, phase, or PSDF. "
        "Equivalent to gwy_data_field_2dfft / gwy_data_field_2dpsdf."
    )

    def process(self, field: DataField, windowing: str, level: str, output: str) -> tuple:
        data = field.data.copy()
        yres, xres = data.shape

        # Level subtraction (Gwyddion-style, before windowing)
        if level == "mean":
            data -= data.mean()
        elif level == "plane":
            # Fit and subtract a plane: z = a + b*x + c*y
            yy, xx = np.mgrid[0:yres, 0:xres]
            xx_f = xx.ravel().astype(np.float64)
            yy_f = yy.ravel().astype(np.float64)
            zz_f = data.ravel()
            A = np.column_stack([np.ones_like(xx_f), xx_f, yy_f])
            coeffs, _, _, _ = np.linalg.lstsq(A, zz_f, rcond=None)
            plane = (coeffs[0] + coeffs[1] * xx + coeffs[2] * yy)
            data -= plane

        # Windowing (Gwyddion uses (i+0.5)/n centred formulation)
        if windowing != "none":
            t_y = (np.arange(yres) + 0.5) / yres
            t_x = (np.arange(xres) + 0.5) / xres
            if windowing == "hann":
                wy = 0.5 - 0.5 * np.cos(2 * np.pi * t_y)
                wx = 0.5 - 0.5 * np.cos(2 * np.pi * t_x)
            elif windowing == "hamming":
                wy = 0.54 - 0.46 * np.cos(2 * np.pi * t_y)
                wx = 0.54 - 0.46 * np.cos(2 * np.pi * t_x)
            elif windowing == "blackman":
                wy = 0.42 - 0.5 * np.cos(2 * np.pi * t_y) + 0.08 * np.cos(4 * np.pi * t_y)
                wx = 0.42 - 0.5 * np.cos(2 * np.pi * t_x) + 0.08 * np.cos(4 * np.pi * t_x)
            else:
                wy = np.ones(yres)
                wx = np.ones(xres)
            data *= np.outer(wy, wx)

        # 2D FFT, shifted so DC is at centre
        F = np.fft.fftshift(np.fft.fft2(data))
        n = xres * yres

        if output == "log_magnitude":
            mag = np.abs(F)
            # Log scale with floor to avoid log(0)
            result = np.log1p(mag)
        elif output == "magnitude":
            result = np.abs(F)
        elif output == "phase":
            result = np.angle(F)
        elif output == "psdf":
            # Gwyddion-equivalent PSDF: |F|^2 * dx * dy / (n * 4π²)
            dx = field.xreal / xres
            dy = field.yreal / yres
            result = (np.abs(F) ** 2) * dx * dy / (n * 4.0 * np.pi ** 2)
        else:
            result = np.abs(F)

        # Calibrate the output field in spatial-frequency units
        if output == "psdf":
            # Gwyddion uses angular frequency: 2π/dx, 2π/dy
            freq_xreal = 2.0 * np.pi * xres / field.xreal
            freq_yreal = 2.0 * np.pi * yres / field.yreal
            z_unit = f"({field.si_unit_z})^2 m^2"
        else:
            freq_xreal = xres / field.xreal
            freq_yreal = yres / field.yreal
            z_unit = field.si_unit_z

        out_field = DataField(
            data=result,
            xreal=freq_xreal,
            yreal=freq_yreal,
            si_unit_xy="1/m",
            si_unit_z=z_unit,
            domain="frequency",
            colormap=field.colormap,
        )
        return (out_field,)


# ---------------------------------------------------------------------------
# CrossSection
# ---------------------------------------------------------------------------

def _extend_to_edges(x1, y1, x2, y2):
    """
    Extend the line through (x1,y1)-(x2,y2) to the boundaries of [0,1]x[0,1].
    Returns the two intersection points (clipped to the unit square).
    """
    dx = x2 - x1
    dy = y2 - y1

    # Collect parametric t values where line hits each boundary
    t_candidates = []
    if abs(dx) > 1e-12:
        for bx in (0.0, 1.0):
            t = (bx - x1) / dx
            y_at_t = y1 + t * dy
            if -1e-9 <= y_at_t <= 1.0 + 1e-9:
                t_candidates.append(t)
    if abs(dy) > 1e-12:
        for by in (0.0, 1.0):
            t = (by - y1) / dy
            x_at_t = x1 + t * dx
            if -1e-9 <= x_at_t <= 1.0 + 1e-9:
                t_candidates.append(t)

    if len(t_candidates) < 2:
        return x1, y1, x2, y2

    t_min = min(t_candidates)
    t_max = max(t_candidates)

    return (
        np.clip(x1 + t_min * dx, 0, 1),
        np.clip(y1 + t_min * dy, 0, 1),
        np.clip(x1 + t_max * dx, 0, 1),
        np.clip(y1 + t_max * dy, 0, 1),
    )


@register_node(display_name="Cross Section")
class CrossSection:
    """Extract a 1-D height profile along an arbitrary line across the image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "x1": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "extend": (["none", "to_edges"],),
                "n_samples": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1}),
            },
            "optional": {
                "point_a": ("COORD",),
                "point_b": ("COORD",),
            },
        }

    RETURN_TYPES = ("LINE",)
    RETURN_NAMES = ("profile",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Extract a cross-section profile along a line between two points. "
        "Drag the markers on the image to set the line endpoints. "
        "Equivalent to gwy_data_field_get_profile."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self, field: DataField,
        x1: float, y1: float, x2: float, y2: float,
        extend: str, n_samples: int,
        point_a=None, point_b=None,
    ) -> tuple:
        from scipy.ndimage import map_coordinates

        # COORD inputs override widget values
        if point_a is not None:
            x1, y1 = float(point_a[0]), float(point_a[1])
        if point_b is not None:
            x2, y2 = float(point_b[0]), float(point_b[1])

        # Remember marker positions (before extend)
        marker_x1, marker_y1 = float(x1), float(y1)
        marker_x2, marker_y2 = float(x2), float(y2)

        xres, yres = field.xres, field.yres

        if extend == "to_edges":
            x1, y1, x2, y2 = _extend_to_edges(
                float(x1), float(y1), float(x2), float(y2),
            )

        # Convert fractional [0,1] to pixel indices [0, res-1]
        px1, py1 = float(x1) * (xres - 1), float(y1) * (yres - 1)
        px2, py2 = float(x2) * (xres - 1), float(y2) * (yres - 1)

        # Number of sample points
        line_len_px = np.hypot(px2 - px1, py2 - py1)
        if n_samples <= 0:
            n_samples = max(2, int(np.ceil(line_len_px)))

        # Sample coordinates along the line
        t = np.linspace(0, 1, n_samples)
        coords_y = py1 + t * (py2 - py1)
        coords_x = px1 + t * (px2 - px1)

        # Interpolate values along the line (cubic spline)
        profile = map_coordinates(field.data, [coords_y, coords_x], order=3, mode="nearest")

        # Broadcast overlay image with marker positions
        if CrossSection._broadcast_overlay_fn is not None:
            # Use the field's native pixel grid for the overlay preview so enlarging
            # the panel keeps the image as sharp as the source data allows.
            image_uri = encode_preview(datafield_to_uint8(field, field.colormap))

            CrossSection._broadcast_overlay_fn(
                CrossSection._current_node_id,
                {
                    "image": image_uri,
                    "x1": marker_x1, "y1": marker_y1,
                    "x2": marker_x2, "y2": marker_y2,
                    "a_locked": point_a is not None,
                    "b_locked": point_b is not None,
                },
            )

        return (profile.astype(np.float64),)


# ---------------------------------------------------------------------------
# LineMath — single scalar measurement from a LINE profile
# ---------------------------------------------------------------------------

def _safe_rq(d):
    """RMS of deviations from mean."""
    return float(np.sqrt(np.mean(d * d)))

# Registry: name → (function(z) → float, unit_label)
# All functions receive the raw 1-D profile as float64.
LINE_OPS: dict[str, tuple] = {}


def _line_op(name, unit=""):
    """Decorator to register a LINE operation."""
    def decorator(fn):
        LINE_OPS[name] = (fn, unit)
        return fn
    return decorator


# ── Basic statistics ──────────────────────────────────────────────────────

@_line_op("min")
def _op_min(z):
    return float(z.min())

@_line_op("max")
def _op_max(z):
    return float(z.max())

@_line_op("mean")
def _op_mean(z):
    return float(z.mean())

@_line_op("median")
def _op_median(z):
    return float(np.median(z))

@_line_op("sum")
def _op_sum(z):
    return float(z.sum())

@_line_op("range")
def _op_range(z):
    return float(z.max() - z.min())

@_line_op("length", unit="pts")
def _op_length(z):
    return float(len(z))

@_line_op("rms")
def _op_rms(z):
    return float(np.sqrt(np.mean(z * z)))


# ── Roughness parameters ──────────────────────────

@_line_op("Ra")
def _op_ra(z):
    return float(np.mean(np.abs(z - z.mean())))

@_line_op("Rq")
def _op_rq(z):
    d = z - z.mean()
    return _safe_rq(d)

@_line_op("Rsk")
def _op_rsk(z):
    d = z - z.mean()
    rq = _safe_rq(d)
    return float(np.mean(d**3) / rq**3) if rq > 0 else 0.0

@_line_op("Rku")
def _op_rku(z):
    d = z - z.mean()
    rq = _safe_rq(d)
    return float(np.mean(d**4) / rq**4) if rq > 0 else 0.0

@_line_op("Rp")
def _op_rp(z):
    return float((z - z.mean()).max())

@_line_op("Rv")
def _op_rv(z):
    return float(-(z - z.mean()).min())

@_line_op("Rt")
def _op_rt(z):
    d = z - z.mean()
    return float(d.max() - d.min())

@_line_op("Dq")
def _op_dq(z):
    """RMS slope (first derivative RMS)."""
    dz = np.diff(z)
    return float(np.sqrt(np.mean(dz * dz)))

@_line_op("Da")
def _op_da(z):
    """Mean absolute slope."""
    return float(np.mean(np.abs(np.diff(z))))


@register_node(display_name="Line Math")
class LineMath:
    """Compute a single scalar value from a LINE profile."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line": ("LINE",),
                "operation": (list(LINE_OPS.keys()),),
            }
        }

    RETURN_TYPES = ("MEASURE_TABLE",)
    RETURN_NAMES = ("result",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute a single scalar measurement from a LINE profile. "
        "Includes basic stats and Gwyddion-convention roughness parameters."
    )

    def process(self, line, operation: str) -> tuple:
        z = np.asarray(line, dtype=np.float64).ravel()
        fn, unit = LINE_OPS[operation]
        value = fn(z)
        table = MeasureTable([{"quantity": operation, "value": value, "unit": unit}])
        return (table,)


# ---------------------------------------------------------------------------
# TableMath — scalar measurement from a numeric record-table column
# ---------------------------------------------------------------------------

TABLE_OPS: dict[str, Callable[[np.ndarray], float]] = {
    "min": lambda values: float(np.min(values)),
    "max": lambda values: float(np.max(values)),
    "avg": lambda values: float(np.mean(values)),
    "mean": lambda values: float(np.mean(values)),
    "median": lambda values: float(np.median(values)),
    "sum": lambda values: float(np.sum(values)),
    "range": lambda values: float(np.max(values) - np.min(values)),
    "std": lambda values: float(np.std(values)),
    "variance": lambda values: float(np.var(values)),
    "count": lambda values: float(len(values)),
}

ARRAY_OPS: dict[str, Callable[[np.ndarray], float]] = {
    "min": lambda values: float(np.min(values)),
    "max": lambda values: float(np.max(values)),
    "avg": lambda values: float(np.mean(values)),
    "mean": lambda values: float(np.mean(values)),
    "median": lambda values: float(np.median(values)),
    "sum": lambda values: float(np.sum(values)),
    "range": lambda values: float(np.max(values) - np.min(values)),
    "std": lambda values: float(np.std(values)),
    "variance": lambda values: float(np.var(values)),
    "rms": lambda values: float(np.sqrt(np.mean(values * values))),
    "count": lambda values: float(values.size),
}


def _square_unit(unit: str) -> str:
    unit = str(unit or "").strip()
    if not unit:
        return ""
    if any(token in unit for token in ("^", "(", ")", "/", "*", " ")):
        return f"({unit})^2"
    return f"{unit}^2"


def _apply_scalar_unit(base_unit: str, operation: str) -> str:
    unit = str(base_unit or "").strip()
    if operation == "count":
        return "count"
    if not unit:
        return ""
    if operation == "variance":
        return _square_unit(unit)
    return unit


def _common_table_unit(table: list, column: str) -> str:
    candidates = []
    seen = set()
    unit_key = f"{column}_unit"

    for row in table:
        if not isinstance(row, dict):
            continue
        unit = None
        if unit_key in row and isinstance(row.get(unit_key), str):
            unit = row.get(unit_key)
        elif column == "value" and isinstance(row.get("unit"), str):
            unit = row.get("unit")
        if unit is None:
            continue
        unit = unit.strip()
        if not unit or unit in seen:
            continue
        seen.add(unit)
        candidates.append(unit)

    if len(candidates) == 1:
        return candidates[0]
    return ""


def _scalar_payload(value: float, unit: str = "") -> dict:
    payload = {"value": float(value)}
    if isinstance(unit, str) and unit.strip():
        payload["unit"] = unit.strip()
    return payload


@register_node(display_name="Table Math")
class TableMath:
    """Compute a scalar reduction over one numeric column in a record table."""

    _broadcast_value_fn = None
    _current_node_id: str = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "table": ("RECORD_TABLE",),
                "column": ("STRING", {
                    "default": "value",
                    "choices_from_table_input": "table",
                }),
                "operation": (list(TABLE_OPS.keys()),),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute a scalar reduction over one numeric record-table column. "
        "Useful for max, min, avg, median, sum, range, std, variance, and count."
    )

    def process(self, table: list, column: str, operation: str) -> tuple:
        if isinstance(table, MeasureTable):
            raise ValueError("Table Math only accepts record tables, not measurement tables.")
        if not isinstance(table, list) or not table:
            raise ValueError("Table Math requires a non-empty record table input.")

        column_name = resolve_table_column_name(table, column)
        values = extract_numeric_table_values(table, column_name)
        if not values:
            raise ValueError(f"Column '{column_name}' has no numeric values.")

        op = TABLE_OPS.get(operation)
        if op is None:
            raise ValueError(f"Unsupported table operation: {operation}")

        result = op(np.asarray(values, dtype=np.float64))
        if TableMath._broadcast_value_fn is not None:
            TableMath._broadcast_value_fn(TableMath._current_node_id, result)
        return (result,)


def extract_numeric_table_values(table: list, column: str) -> list[float]:
    values = []
    for row in table:
        if not isinstance(row, dict) or column not in row:
            continue
        value = row[column]
        if isinstance(value, bool):
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            values.append(numeric)
    return values


def resolve_table_column_name(table: list, column: str) -> str:
    requested = str(column or "").strip()
    if requested:
        return requested

    if extract_numeric_table_values(table, "value"):
        return "value"

    numeric_columns = []
    seen = set()
    for row in table:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            if extract_numeric_table_values(table, key):
                numeric_columns.append(key)

    if len(numeric_columns) == 1:
        return numeric_columns[0]
    if not numeric_columns:
        raise ValueError("Table Math could not find any numeric columns in the input table.")
    raise ValueError(
        "Table Math found multiple numeric columns; set the column name explicitly."
    )


@register_node(display_name="Stats")
class Stats:
    """Polymorphic scalar stats node for LINE, RECORD_TABLE, DATA_FIELD, or IMAGE inputs."""

    _broadcast_value_fn = None
    _current_node_id: str = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("STATS_SOURCE",),
                "column": ("STRING", {
                    "default": "value",
                    "choices_from_table_input": "input",
                    "show_when_source_type": {
                        "input": ["RECORD_TABLE"],
                    },
                }),
                "operation": ("STRING", {
                    "default": "mean",
                    "choices_by_source_type": {
                        "LINE": list(LINE_OPS.keys()),
                        "RECORD_TABLE": list(TABLE_OPS.keys()),
                        "DATA_FIELD": list(ARRAY_OPS.keys()),
                        "IMAGE": list(ARRAY_OPS.keys()),
                    },
                    "source_type_input": "input",
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute a contextual scalar statistic from a LINE, record table, DATA_FIELD, or IMAGE. "
        "The available operations adapt to the connected input type."
    )

    def process(self, input, operation: str, column: str = "value") -> tuple:
        source_type, values, resolved_column = self._resolve_input_values(input, column)

        if source_type == "RECORD_TABLE":
            ops = TABLE_OPS
        elif source_type == "LINE":
            ops = LINE_OPS
        else:
            ops = ARRAY_OPS

        if operation not in ops:
            raise ValueError(f"Operation '{operation}' is not valid for {source_type} input.")

        op_entry = ops[operation]
        fn = op_entry[0] if isinstance(op_entry, tuple) else op_entry
        result = fn(values)
        if Stats._broadcast_value_fn is not None:
            Stats._broadcast_value_fn(
                Stats._current_node_id,
                _scalar_payload(result, self._resolve_output_unit(input, source_type, resolved_column, operation)),
            )
        return (result,)

    def _resolve_output_unit(self, input_value, source_type: str, column: str | None, operation: str) -> str:
        if source_type == "DATA_FIELD" and isinstance(input_value, DataField):
            return _apply_scalar_unit(input_value.si_unit_z, operation)

        if source_type == "LINE":
            line_entry = LINE_OPS.get(operation)
            explicit_unit = line_entry[1] if isinstance(line_entry, tuple) and len(line_entry) > 1 else ""
            return _apply_scalar_unit(explicit_unit, operation)

        if source_type == "RECORD_TABLE" and isinstance(input_value, list) and column:
            return _apply_scalar_unit(_common_table_unit(input_value, column), operation)

        return ""

    def _resolve_input_values(self, input_value, column: str) -> tuple[str, np.ndarray, str | None]:
        if isinstance(input_value, DataField):
            values = np.asarray(input_value.data, dtype=np.float64)
            return ("DATA_FIELD", values.ravel(), None)

        if isinstance(input_value, MeasureTable):
            raise ValueError("Stats only accepts record tables, not measurement tables.")

        if isinstance(input_value, list):
            if not input_value:
                raise ValueError("Stats requires a non-empty record table input.")
            column_name = resolve_table_column_name(input_value, column)
            values = extract_numeric_table_values(input_value, column_name)
            if not values:
                raise ValueError(f"Column '{column_name}' has no numeric values.")
            return ("RECORD_TABLE", np.asarray(values, dtype=np.float64), column_name)

        if isinstance(input_value, np.ndarray):
            values = np.asarray(input_value, dtype=np.float64)
            if values.size == 0:
                raise ValueError("Stats requires a non-empty input.")
            if values.ndim == 1:
                return ("LINE", values.ravel(), None)
            return ("IMAGE", values.ravel(), None)

        raise ValueError(f"Unsupported Stats input type: {type(input_value).__name__}")
