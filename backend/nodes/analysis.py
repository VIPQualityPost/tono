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
from backend.node_registry import register_node
from backend.data_types import DataField


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

    RETURN_TYPES = ("TABLE",)
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

        table = [
            {"quantity": "min",      "value": float(d.min()),    "unit": field.si_unit_z},
            {"quantity": "max",      "value": float(d.max()),    "unit": field.si_unit_z},
            {"quantity": "mean",     "value": mean,              "unit": field.si_unit_z},
            {"quantity": "RMS",      "value": rms,               "unit": field.si_unit_z},
            {"quantity": "median",   "value": float(np.median(d)), "unit": field.si_unit_z},
            {"quantity": "skewness", "value": skewness,          "unit": ""},
            {"quantity": "kurtosis", "value": kurtosis,          "unit": ""},
            {"quantity": "range",    "value": float(d.max() - d.min()), "unit": field.si_unit_z},
        ]
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
            }
        }

    RETURN_TYPES = ("LINE", "LINE")
    RETURN_NAMES = ("counts", "bin_centers")
    FUNCTION = "process"
    CATEGORY = "analysis"
    DESCRIPTION = (
        "Compute the height distribution histogram (DH). "
        "Equivalent to gwy_data_field_dh."
    )

    def process(self, field: DataField, n_bins: int) -> tuple:
        counts, bin_edges = np.histogram(field.data.ravel(), bins=int(n_bins))
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        return (counts.astype(np.float64), bin_centers)


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
                "x1": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
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
        import io, base64
        from matplotlib.figure import Figure

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
            fig = Figure(figsize=(3, 3), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(field.data, cmap="viridis", aspect="auto")
            ax.axis("off")
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
            buf.seek(0)
            image_uri = "data:image/png;base64," + base64.b64encode(buf.read()).decode()

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

    RETURN_TYPES = ("TABLE",)
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
        table = [{"quantity": operation, "value": value, "unit": unit}]
        return (table,)
