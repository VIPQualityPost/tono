"""
Exporter for LINE values (1-D profiles as LineData or bare ndarrays).

PNG / TIFF render a plot image via Pillow; CSV / JSON / NPZ save the raw
(x, y, unit) arrays. The plot renderer is self-contained (no matplotlib
dependency) and handles SI-prefix axis labels.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from backend.data_types import LineData, _PREFIXABLE_UNITS, _SI_PREFIXES
from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("LINE",)

FORMATS: dict[str, FormatSpec] = {
    "PNG":  FormatSpec(ext=".png",  round_trip=False, label="PNG plot"),
    "TIFF": FormatSpec(ext=".tiff", round_trip=False, label="TIFF plot"),
    "CSV":  FormatSpec(ext=".csv",  round_trip=True,  label="CSV"),
    "NPZ":  FormatSpec(ext=".npz",  round_trip=False, label="NumPy (.npz)"),
    "JSON": FormatSpec(ext=".json", round_trip=True,  label="JSON"),
}


def save(path: Path, value, format_name: str, *, plot_title: str = "", **_opts) -> None:
    line = value if isinstance(value, LineData) else LineData(data=np.asarray(value).ravel())

    y = np.asarray(line.data, dtype=np.float64).ravel()
    if line.x_axis is not None:
        x = np.asarray(line.x_axis, dtype=np.float64).ravel()[: len(y)]
    else:
        x = np.arange(len(y), dtype=np.float64)

    if format_name in ("PNG", "TIFF"):
        _save_line_plot(path, x, y, line.x_unit, line.y_unit, plot_title, format_name)
        return
    if format_name == "CSV":
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["x", "y", "x_unit", "y_unit"])
            for xv, yv in zip(x, y):
                writer.writerow([xv, yv, line.x_unit, line.y_unit])
        return
    if format_name == "NPZ":
        np.savez(str(path), x=x, y=y)
        return
    if format_name == "JSON":
        path.write_text(
            json.dumps({
                "x": x.tolist(),
                "y": y.tolist(),
                "x_unit": line.x_unit,
                "y_unit": line.y_unit,
            }, indent=2),
            encoding="utf-8",
        )
        return
    raise ValueError(f"Format {format_name!r} is not supported for LINE.")


def _save_line_plot(
    path: Path,
    x: np.ndarray,
    y: np.ndarray,
    x_unit: str,
    y_unit: str,
    title: str,
    format_name: str,
) -> None:
    """Render a simple PNG/TIFF line plot with SI-prefixed axes.

    Intentionally self-contained (Pillow only, no matplotlib) so that builds
    stay lean. Layout is fixed 1200×750 with 5×5 grid and a single blue line.
    """
    from PIL import Image, ImageDraw, ImageFont

    w, h = 1200, 750
    bg = (255, 255, 255)
    line_color = (79, 142, 247)  # #4f8ef7
    grid_color = (200, 200, 200)
    text_color = (60, 60, 60)
    margin = {"left": 80, "right": 30, "top": 50, "bottom": 60}

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 11)
        font_title = ImageFont.truetype("DejaVuSans.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font
        font_title = font

    pw = w - margin["left"] - margin["right"]
    ph = h - margin["top"] - margin["bottom"]

    def _si_scale(unit: str, vmin: float, vmax: float) -> tuple[float, str]:
        """Pick the best SI prefix for an axis range. Returns (divisor, prefixed_unit)."""
        unit = (unit or "").strip()
        if not unit or unit not in _PREFIXABLE_UNITS:
            return 1.0, unit if unit else ""
        peak = max(abs(vmin), abs(vmax))
        if peak == 0:
            return 1.0, unit
        for scale, prefix in _SI_PREFIXES:
            if peak / scale >= 1.0:
                return scale, f"{prefix}{unit}"
        return _SI_PREFIXES[-1][0], f"{_SI_PREFIXES[-1][1]}{unit}"

    xmin, xmax = float(np.nanmin(x)), float(np.nanmax(x))
    ymin, ymax = float(np.nanmin(y)), float(np.nanmax(y))

    x_scale, x_label = _si_scale(x_unit, xmin, xmax)
    y_scale, y_label = _si_scale(y_unit, ymin, ymax)
    if not x_label:
        x_label = "x"
    if not y_label:
        y_label = "y"

    x = x / x_scale
    y = y / y_scale
    xmin, xmax = xmin / x_scale, xmax / x_scale
    ymin, ymax = ymin / y_scale, ymax / y_scale

    if ymax == ymin:
        ymin, ymax = ymin - 1, ymax + 1
    if xmax == xmin:
        xmax = xmin + 1
    ypad = (ymax - ymin) * 0.05
    ymin -= ypad
    ymax += ypad

    def to_px(xv: float, yv: float) -> tuple[float, float]:
        px = margin["left"] + (xv - xmin) / (xmax - xmin) * pw
        py = margin["top"] + (1.0 - (yv - ymin) / (ymax - ymin)) * ph
        return px, py

    for i in range(6):
        gy = ymin + (ymax - ymin) * i / 5
        _, py = to_px(xmin, gy)
        draw.line([(margin["left"], py), (margin["left"] + pw, py)], fill=grid_color, width=1)
        label = f"{gy:.4g}"
        draw.text((margin["left"] - 8, py - 6), label, fill=text_color, font=font_small, anchor="rm")

        gx = xmin + (xmax - xmin) * i / 5
        px, _ = to_px(gx, ymin)
        draw.line([(px, margin["top"]), (px, margin["top"] + ph)], fill=grid_color, width=1)
        label = f"{gx:.4g}"
        draw.text((px, margin["top"] + ph + 6), label, fill=text_color, font=font_small, anchor="mt")

    n = len(y)
    step = max(1, n // pw)
    xs, ys = x[::step], y[::step]
    pts = [to_px(float(xs[i]), float(ys[i])) for i in range(len(xs))]
    if len(pts) > 1:
        draw.line(pts, fill=line_color, width=2)

    draw.rectangle(
        [margin["left"], margin["top"], margin["left"] + pw, margin["top"] + ph],
        outline=(100, 100, 100), width=1,
    )
    draw.text((margin["left"] + pw // 2, h - 10), x_label, fill=text_color, font=font, anchor="mb")

    y_label_img = Image.new("RGBA", (200, 20), (0, 0, 0, 0))
    y_draw = ImageDraw.Draw(y_label_img)
    y_draw.text((100, 10), y_label, fill=text_color, font=font, anchor="mm")
    y_label_img = y_label_img.rotate(90, expand=True)
    img.paste(y_label_img, (2, margin["top"] + ph // 2 - y_label_img.height // 2), y_label_img)

    if title and title.strip():
        draw.text((w // 2, 10), title.strip(), fill=text_color, font=font_title, anchor="mt")

    ext = ".png" if format_name == "PNG" else ".tiff"
    img.save(str(path.with_suffix(ext)))
