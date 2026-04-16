"""
Shared helper functions for tono nodes.
"""

from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np

from backend.runtime_paths import demo_dir

# ---------------------------------------------------------------------------
# Scalar payload helpers  (from display.py)
# ---------------------------------------------------------------------------

_SI_PREFIXES: dict[str, float] = {
    'Y': 1e24, 'Z': 1e21, 'E': 1e18, 'P': 1e15, 'T': 1e12,
    'G': 1e9,  'M': 1e6,  'k': 1e3,
    'm': 1e-3, 'u': 1e-6, 'µ': 1e-6, 'n': 1e-9, 'p': 1e-12,
    'f': 1e-15, 'a': 1e-18, 'z': 1e-21, 'y': 1e-24,
}

_PREFIXABLE_UNITS: frozenset[str] = frozenset({
    'm', 's', 'A', 'V', 'W', 'Hz', 'F', 'C', 'J', 'N', 'Pa',
    'T', 'H', 'S', 'g', 'K', 'Ohm', 'ohm', 'Ω',
})

_NUMBER_RE = re.compile(
    r'^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)?$'
)


def parse_number_with_unit(text: str) -> tuple[float, str]:
    """Parse a string like '1.5 nm' into (1.5e-9, 'm').

    The numeric part may use scientific notation. The unit is stripped of any
    recognised SI prefix and the raw value is scaled accordingly, so the
    returned float is always in the base SI unit.  Units that are not
    prefixable are returned unchanged alongside the unscaled value.

    Examples::

        parse_number_with_unit("1 um")   → (1e-6, "m")
        parse_number_with_unit("500 nm") → (5e-7, "m")
        parse_number_with_unit("3.14")   → (3.14, "")
        parse_number_with_unit("2 kHz")  → (2000.0, "Hz")
    """
    text = text.strip()
    if not text:
        return 0.0, ""

    m = _NUMBER_RE.match(text)
    if not m:
        raise ValueError(f"Cannot parse number: {text!r}")

    numeric = float(m.group(1))
    unit_str = (m.group(2) or "").strip()

    if not unit_str:
        return numeric, ""

    # Try prefix + base-unit split (handle multi-byte µ as a prefix)
    if len(unit_str) >= 2:
        prefix_char = unit_str[0]
        rest = unit_str[1:]
        if prefix_char in _SI_PREFIXES and rest in _PREFIXABLE_UNITS:
            return numeric * _SI_PREFIXES[prefix_char], rest

    return numeric, unit_str


def _scalar_payload(value: float, unit: str = "") -> dict:
    payload = {"value": float(value)}
    if isinstance(unit, str) and unit.strip():
        payload["unit"] = unit.strip()
    return payload


# ---------------------------------------------------------------------------
# Measurement helpers  (from display.py — used by ValueIO)
# ---------------------------------------------------------------------------

def _measurement_names(table: list) -> list[str]:
    names = []
    for row in table:
        if not isinstance(row, dict):
            continue
        quantity = row.get("quantity")
        if isinstance(quantity, str) and quantity and quantity not in names:
            names.append(quantity)
    return names


def _measurement_entry(table: list, selection: str) -> dict:
    names = _measurement_names(table)
    if not names:
        raise ValueError("Measurement table has no selectable rows.")

    target = selection if selection in names else names[0]
    for row in table:
        if isinstance(row, dict) and row.get("quantity") == target:
            return row

    raise ValueError(f"Measurement '{target}' was not found.")


def _measurement_value(table: list, selection: str) -> float:
    row = _measurement_entry(table, selection)
    value = row.get("value")
    if isinstance(value, bool):
        raise ValueError(f"Measurement '{row.get('quantity', selection)}' does not have a numeric value.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Measurement '{row.get('quantity', selection)}' does not have a numeric value.") from exc
    if np.isfinite(numeric):
        return numeric
    raise ValueError(f"Measurement '{row.get('quantity', selection)}' does not have a numeric value.")


def _render_annotation_text(text: str, size_px: int, color: tuple[int, int, int]):
    from PIL import Image, ImageDraw, ImageFont

    size_px = max(8, int(round(size_px)))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size_px)
        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        bbox = probe_draw.textbbox((0, 0), text, font=font)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        text_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)
        text_draw.text((-bbox[0], -bbox[1]), text, font=font, fill=(*color, 255))
        return text_image
    except Exception:
        font = ImageFont.load_default()
        probe = Image.new("L", (1, 1), 0)
        probe_draw = ImageDraw.Draw(probe)
        bbox = probe_draw.textbbox((0, 0), text, font=font)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((-bbox[0], -bbox[1]), text, font=font, fill=255)

        scale = max(1.0, size_px / max(1, height))
        scaled_width = max(1, int(round(width * scale)))
        scaled_height = max(1, int(round(height * scale)))
        resampling = getattr(Image, "Resampling", Image)
        scaled_mask = mask.resize((scaled_width, scaled_height), resample=resampling.BILINEAR)

        text_image = Image.new("RGBA", (scaled_width, scaled_height), (*color, 0))
        text_image.putalpha(scaled_mask)
        return text_image


def _import_ibw_loader():
    """Import igor's binary wave loader with NumPy 2 compatibility."""
    if not hasattr(np, "complex"):
        # igor 0.3 still references np.complex at import time.
        setattr(np, "complex", complex)

    try:
        from igor.binarywave import load as load_ibw
    except ImportError:
        raise ImportError("Install 'igor' package to load .ibw files: pip install igor")

    return load_ibw


# ---------------------------------------------------------------------------
# Markup helpers  (from display.py — used by Markup)
# ---------------------------------------------------------------------------

def _normalize_markup_color(color: object, default: str = "#ffd54f") -> str:
    if isinstance(color, str):
        text = color.strip()
        if len(text) == 4 and text.startswith("#"):
            text = "#" + "".join(ch * 2 for ch in text[1:])
        if len(text) == 7 and text.startswith("#"):
            try:
                int(text[1:], 16)
                return text.lower()
            except ValueError:
                pass
    return default


def _parse_markup_shapes(raw_shapes) -> list[dict]:
    if isinstance(raw_shapes, str):
        try:
            raw_shapes = json.loads(raw_shapes or "[]")
        except json.JSONDecodeError:
            raw_shapes = []

    if not isinstance(raw_shapes, list):
        return []

    parsed = []
    for shape in raw_shapes:
        if not isinstance(shape, dict):
            continue

        kind = str(shape.get("kind", "")).strip().lower()
        if kind not in {"line", "rectangle", "circle", "arrow"}:
            continue

        try:
            x1 = float(shape.get("x1"))
            y1 = float(shape.get("y1"))
            x2 = float(shape.get("x2"))
            y2 = float(shape.get("y2"))
            width = int(round(float(shape.get("width", 3))))
        except (TypeError, ValueError):
            continue

        coords = [x1, y1, x2, y2]
        if not all(np.isfinite(value) for value in coords):
            continue

        parsed.append({
            "kind": kind,
            "x1": float(np.clip(x1, 0.0, 1.0)),
            "y1": float(np.clip(y1, 0.0, 1.0)),
            "x2": float(np.clip(x2, 0.0, 1.0)),
            "y2": float(np.clip(y2, 0.0, 1.0)),
            "width": max(1, min(128, width)),
            "color": _normalize_markup_color(shape.get("color")),
        })

    return parsed


def _draw_arrow(draw, start, end, color, width):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = float(np.hypot(dx, dy))
    if length <= 1e-6:
        radius = max(1.0, width / 2.0)
        draw.ellipse(
            (start[0] - radius, start[1] - radius, start[0] + radius, start[1] + radius),
            fill=color,
        )
        return

    ux = dx / length
    uy = dy / length
    head_length = max(10.0, width * 4.0)
    head_width = max(8.0, width * 3.0)
    shaft_end = (
        end[0] - ux * head_length,
        end[1] - uy * head_length,
    )

    draw.line((start, shaft_end), fill=color, width=width)

    px = -uy
    py = ux
    left = (
        shaft_end[0] + px * head_width / 2.0,
        shaft_end[1] + py * head_width / 2.0,
    )
    right = (
        shaft_end[0] - px * head_width / 2.0,
        shaft_end[1] - py * head_width / 2.0,
    )
    draw.polygon([end, left, right], fill=color)


def _render_markup_image(image, shapes):
    from PIL import Image as PILImage, ImageDraw
    from backend.data_types import image_to_uint8

    base = image_to_uint8(image)
    if base.ndim == 2:
        base = np.repeat(base[:, :, np.newaxis], 3, axis=2)

    canvas = PILImage.fromarray(base.copy())
    draw = ImageDraw.Draw(canvas)
    height, width = base.shape[:2]

    for shape in shapes:
        x1 = float(shape["x1"]) * width
        y1 = float(shape["y1"]) * height
        x2 = float(shape["x2"]) * width
        y2 = float(shape["y2"]) * height
        color = str(shape["color"])
        stroke_width = int(shape["width"])
        kind = str(shape["kind"])

        if kind == "line":
            draw.line(((x1, y1), (x2, y2)), fill=color, width=stroke_width)
        elif kind == "rectangle":
            draw.rectangle((x1, y1, x2, y2), outline=color, width=stroke_width)
        elif kind == "circle":
            draw.ellipse((x1, y1, x2, y2), outline=color, width=stroke_width)
        elif kind == "arrow":
            _draw_arrow(draw, (x1, y1), (x2, y2), color, stroke_width)

    return np.asarray(canvas, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Mask helpers  (from mask.py — used by multiple mask nodes)
# ---------------------------------------------------------------------------

def mask_to_bool(mask: np.ndarray) -> np.ndarray:
    """Convert a uint8 mask (0/255) to a boolean array."""
    return np.asarray(mask) > 127


def bool_to_mask(binary: np.ndarray) -> np.ndarray:
    """Convert a boolean array to a uint8 mask (0/255)."""
    return np.asarray(binary, dtype=np.uint8) * 255


def coerce_physical_square(
    left: float, top: float, right: float, bottom: float,
    xreal: float, yreal: float,
) -> tuple[float, float, float, float]:
    """Shrink the longer physical side so the rectangle is a physical square,
    anchored at (left, top)."""
    side_phys = min((right - left) * xreal, (bottom - top) * yreal)
    if xreal > 0:
        right = left + side_phys / xreal
    if yreal > 0:
        bottom = top + side_phys / yreal
    return left, top, right, bottom


def normalize_mask(
    mask: np.ndarray | None, shape: tuple[int, int],
) -> np.ndarray | None:
    """Validate mask shape and convert from uint8 to boolean."""
    if mask is None:
        return None
    mask_array = np.asarray(mask)
    if mask_array.shape[:2] != shape:
        raise ValueError(
            f"Mask shape {mask_array.shape} does not match field shape {shape}."
        )
    return mask_to_bool(mask_array)


def _mask_overlay(field, mask):
    from backend.data_types import datafield_to_uint8
    grey = datafield_to_uint8(field, "gray")
    mask_bool = mask_to_bool(mask)
    if not np.any(mask_bool):
        return grey

    overlay = grey.copy()
    red = overlay[..., 0]
    green = overlay[..., 1]
    blue = overlay[..., 2]

    red_vals = red[mask_bool].astype(np.uint16)
    green_vals = green[mask_bool].astype(np.uint16)
    blue_vals = blue[mask_bool].astype(np.uint16)
    red[mask_bool] = ((red_vals * 55) + (255 * 45) + 50) // 100
    green[mask_bool] = ((green_vals * 55) + 50) // 100
    blue[mask_bool] = ((blue_vals * 55) + 50) // 100
    return overlay


@lru_cache(maxsize=128)
def _mask_structure(radius: int, shape: str):
    radius = max(1, int(radius))
    if shape == "disk":
        y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
        struct = (x * x + y * y) <= radius * radius
    else:
        size = 2 * radius + 1
        struct = np.ones((size, size), dtype=bool)
    struct.setflags(write=False)
    return struct


def _clamp_fraction(value) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _parse_mask_strokes(mask_paths) -> list[dict]:
    if isinstance(mask_paths, list):
        raw_strokes = mask_paths
    elif isinstance(mask_paths, str) and mask_paths.strip():
        try:
            parsed = json.loads(mask_paths)
        except json.JSONDecodeError:
            return []
        raw_strokes = parsed if isinstance(parsed, list) else []
    else:
        return []

    strokes = []
    for stroke in raw_strokes:
        if not isinstance(stroke, dict):
            continue
        raw_points = stroke.get("points")
        if not isinstance(raw_points, list):
            continue

        points = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            if "x" not in point or "y" not in point:
                continue
            points.append({
                "x": _clamp_fraction(point.get("x")),
                "y": _clamp_fraction(point.get("y")),
            })

        if not points:
            continue

        try:
            size = max(1, int(round(float(stroke.get("size", 1)))))
        except (TypeError, ValueError):
            size = 1

        strokes.append({
            "size": size,
            "points": points,
        })

    return strokes


def _rasterize_mask(width, height, strokes, default_pen_size):
    from PIL import Image as PILImage, ImageDraw

    width = max(1, int(width))
    height = max(1, int(height))
    default_pen_size = max(1, int(default_pen_size))

    mask_image = PILImage.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_image)

    for stroke in strokes:
        points = stroke.get("points") or []
        if not points:
            continue

        size = stroke.get("size", default_pen_size)
        try:
            size = max(1, int(round(float(size))))
        except (TypeError, ValueError):
            size = default_pen_size

        pixel_points = []
        for point in points:
            px = int(round(_clamp_fraction(point.get("x")) * (width - 1)))
            py = int(round(_clamp_fraction(point.get("y")) * (height - 1)))
            pixel_points.append((px, py))

        radius = max(0.5, size / 2.0)

        if len(pixel_points) == 1:
            x, y = pixel_points[0]
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
            continue

        draw.line(pixel_points, fill=255, width=size)
        for x, y in pixel_points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)

    return np.asarray(mask_image, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Path / directory helpers  (from io.py)
# ---------------------------------------------------------------------------

DEMO_DIR = demo_dir()

_MAX_SAVE_FIELDS = 8

from backend.importers import all_extensions, get_importer

_PATH_COMPATIBLE_EXTENSIONS = all_extensions()


def list_channels(filepath: str) -> list[dict]:
    path = Path(filepath)
    if not path.exists():
        return [{"name": "field", "type": "DATA_FIELD"}]

    importer = get_importer(path.suffix.lower())
    if importer is None:
        return [{"name": "field", "type": "DATA_FIELD"}]

    try:
        names = importer.channel_names(path)
        if names:
            return [{"name": n, "type": "DATA_FIELD"} for n in names]
    except Exception:
        pass
    return [{"name": "field", "type": "DATA_FIELD"}]


def list_folder_paths(folderpath: str) -> list[dict]:
    path = Path(folderpath)
    if not path.exists() or not path.is_dir():
        return []

    resolved_dir = str(path.resolve())
    results = [{"name": "directory", "type": "DIRECTORY", "path": resolved_dir}]
    for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_file() or entry.name.startswith("."):
            continue
        if entry.suffix.lower() not in _PATH_COMPATIBLE_EXTENSIONS:
            continue
        results.append({"name": entry.name, "type": "FILE_PATH", "path": str(entry.resolve())})
    return results


def _list_demo_files() -> list[str]:
    if not DEMO_DIR.exists():
        return []
    return sorted(
        f.name for f in DEMO_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in _PATH_COMPATIBLE_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# Butterworth / FFT helpers  (from filters.py — used by FFTFilter
# ---------------------------------------------------------------------------

def _butterworth_lp(freq, cutoff, order):
    with np.errstate(divide="ignore", over="ignore"):
        return 1.0 / (1.0 + (freq / cutoff) ** (2 * order))


def _butterworth_hp(freq, cutoff, order):
    with np.errstate(divide="ignore", invalid="ignore"):
        h = 1.0 / (1.0 + (cutoff / freq) ** (2 * order))
    h = np.where(np.isfinite(h), h, 0.0)
    return h


def _build_1d_transfer(n, filter_type, cutoff, cutoff_high, order):
    freq = np.linspace(0, 1, n // 2 + 1)

    if filter_type == "lowpass":
        H = _butterworth_lp(freq, cutoff, order)
    elif filter_type == "highpass":
        H = _butterworth_hp(freq, cutoff, order)
    elif filter_type == "bandpass":
        H = _butterworth_hp(freq, cutoff, order) * _butterworth_lp(freq, cutoff_high, order)
    elif filter_type == "notch":
        bp = _butterworth_hp(freq, cutoff, order) * _butterworth_lp(freq, cutoff_high, order)
        H = 1.0 - bp
    else:
        H = np.ones_like(freq)
    return H


@lru_cache(maxsize=64)
def _cached_1d_transfer(n, filter_type, cutoff, cutoff_high, order):
    transfer = _build_1d_transfer(n, filter_type, cutoff, cutoff_high, order)
    transfer.setflags(write=False)
    return transfer


@lru_cache(maxsize=32)
def _fft_radius_grid(yres, xres):
    fy = np.fft.fftfreq(yres)[:, np.newaxis] * 2.0
    fx = np.fft.rfftfreq(xres)[np.newaxis, :] * 2.0
    radius = np.sqrt(fx * fx + fy * fy) / np.sqrt(2.0)
    np.clip(radius, 0.0, 1.0, out=radius)
    radius.setflags(write=False)
    return radius


@lru_cache(maxsize=128)
def _cached_2d_transfer(yres, xres, filter_type, cutoff, cutoff_high, order):
    radius = _fft_radius_grid(yres, xres)

    if filter_type == "lowpass":
        transfer = _butterworth_lp(radius, cutoff, order)
    elif filter_type == "highpass":
        transfer = _butterworth_hp(radius, cutoff, order)
    elif filter_type == "bandpass":
        transfer = _butterworth_hp(radius, cutoff, order) * _butterworth_lp(radius, cutoff_high, order)
    elif filter_type == "notch":
        band = _butterworth_hp(radius, cutoff, order) * _butterworth_lp(radius, cutoff_high, order)
        transfer = 1.0 - band
    else:
        transfer = np.ones_like(radius)

    transfer.setflags(write=False)
    return transfer


# ---------------------------------------------------------------------------
# Cross-section and stats helpers  (from analysis.py)
# ---------------------------------------------------------------------------

def _extend_to_edges(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1

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


def _safe_rq(d):
    return float(np.sqrt(np.mean(d * d)))


LINE_OPS: dict[str, tuple] = {}


def _line_op(name, unit=""):
    def decorator(fn):
        LINE_OPS[name] = (fn, unit)
        return fn
    return decorator


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
    dz = np.diff(z)
    return float(np.sqrt(np.mean(dz * dz)))

@_line_op("Da")
def _op_da(z):
    return float(np.mean(np.abs(np.diff(z))))


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


def apply_masking(data: np.ndarray, mask: np.ndarray | None, masking: str) -> np.ndarray:
    """Return a boolean validity array from a mask and masking mode.

    Returns a bool array the same shape as *data* indicating which pixels
    should be included in calculations.
    """
    if mask is None or masking == "ignore":
        return np.ones(data.shape, dtype=bool)
    if masking == "include":
        return np.asarray(mask, dtype=bool)
    if masking == "exclude":
        return ~np.asarray(mask, dtype=bool)
    raise ValueError(f"Unknown masking mode: {masking}")


def masked_values(data: np.ndarray, mask: np.ndarray | None, masking: str) -> np.ndarray:
    """Return the 1-D subset of *data* selected by the masking mode."""
    if mask is None or masking == "ignore":
        return data
    if masking == "include":
        return data[mask]
    if masking == "exclude":
        return data[~mask]
    raise ValueError(f"Unknown masking mode: {masking}")


def emit_mask_preview(field, mask_uint8: np.ndarray) -> None:
    """Emit a standard mask-on-field preview if *field* is not None."""
    if field is None:
        return
    from backend.execution_context import emit_preview
    from backend.data_types import encode_preview
    emit_preview(encode_preview(_mask_overlay(field, mask_uint8)))


def histogram_with_centers(data: np.ndarray, bins: int = 256):
    """Compute histogram and return (counts_float64, bin_centers)."""
    raw_counts, bin_edges = np.histogram(data.ravel(), bins=int(bins))
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    counts = raw_counts.astype(np.float64)
    return counts, bin_centers


def frac_to_index(axis: np.ndarray, frac: float) -> int:
    """Map a fractional position [0, 1] to the nearest index in *axis*."""
    n = len(axis)
    if n <= 1:
        return 0
    lo = float(axis[0])
    hi = float(axis[-1])
    if hi == lo:
        return 0
    target = lo + frac * (hi - lo)
    return int(np.argmin(np.abs(axis - target)))


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
        raise ValueError("Stats could not find any numeric columns in the input table.")
    raise ValueError(
        "Stats found multiple numeric columns; set the column name explicitly."
    )
