"""
Core data types for argonode.

DataField mirrors Gwyddion's GwyDataField structure:
  xres, yres  – pixel dimensions
  xreal, yreal – physical dimensions in metres
  xoff, yoff   – position offset in metres
  si_unit_xy   – lateral unit string (e.g. "m", "nm")
  si_unit_z    – height/value unit string (e.g. "m", "V", "A")
  domain       – "spatial" or "frequency" (set by FFT nodes)
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
import numpy as np


COLORMAPS = ("viridis", "gray", "hot", "jet", "plasma", "inferno", "terrain",
             "cividis", "magma", "copper", "afmhot")
DEFAULT_CUSTOM_COLORMAP_STOPS = (
    {"position": 0.0, "color": "#440154"},
    {"position": 1.0, "color": "#fde725"},
)
SYSTEM_DEFAULT_FONT = "System Default"
CUSTOM_FILE_FONT = "Custom File"
PREVIEW_MARKUP_REFERENCE_DIM = 512


class RecordTable(list):
    """Tabular rows with a shared schema, e.g. particle statistics."""


class MeasureTable(list):
    """Named scalar measurements, typically rows of quantity/value/unit."""


def _normalize_hex_color(color: Any, default: str = "#000000") -> str:
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


def _hex_to_rgb01(color: str) -> tuple[float, float, float]:
    normalized = _normalize_hex_color(color)
    return (
        int(normalized[1:3], 16) / 255.0,
        int(normalized[3:5], 16) / 255.0,
        int(normalized[5:7], 16) / 255.0,
    )


def _normalize_custom_colormap_stops(raw_stops: Any) -> list[dict[str, float | str]] | None:
    if not isinstance(raw_stops, list):
        return None

    parsed = []
    for stop in raw_stops:
        if not isinstance(stop, dict):
            continue
        try:
            position = float(stop.get("position"))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(position):
            continue
        parsed.append({
            "position": float(np.clip(position, 0.0, 1.0)),
            "color": _normalize_hex_color(stop.get("color"), "#000000"),
        })

    if len(parsed) < 2:
        return None

    parsed.sort(key=lambda stop: stop["position"])
    unique: list[dict[str, float | str]] = []
    for stop in parsed:
        if unique and abs(float(stop["position"]) - float(unique[-1]["position"])) < 1e-9:
            unique[-1] = stop
        else:
            unique.append(stop)

    if len(unique) < 2:
        return None

    unique[0] = {"position": 0.0, "color": unique[0]["color"]}
    unique[-1] = {"position": 1.0, "color": unique[-1]["color"]}
    return unique


def normalize_colormap_spec(colormap: Any, fallback: Any = "viridis") -> str | dict[str, Any]:
    if isinstance(colormap, str):
        if colormap in COLORMAPS:
            return colormap
    elif isinstance(colormap, dict):
        mode = str(colormap.get("mode", "")).strip().lower()
        preset = colormap.get("preset")
        if isinstance(preset, str) and preset in COLORMAPS:
            if mode == "preset" or "stops" not in colormap:
                return {"mode": "preset", "preset": preset}
        stops = _normalize_custom_colormap_stops(colormap.get("stops"))
        if stops is not None:
            return {"mode": "custom", "stops": stops}

    if fallback is colormap:
        return "viridis"
    return normalize_colormap_spec(fallback, fallback="viridis")


def resolve_colormap_input(
    selection: Any = "auto",
    *,
    colormap_input: Any = None,
    inherited: Any = None,
    default: Any = "gray",
) -> str | dict[str, Any]:
    if colormap_input is not None:
        return normalize_colormap_spec(colormap_input, fallback=inherited if inherited is not None else default)

    if isinstance(selection, str) and selection != "auto":
        return normalize_colormap_spec(selection, fallback=inherited if inherited is not None else default)

    if inherited is not None:
        return normalize_colormap_spec(inherited, fallback=default)

    return normalize_colormap_spec(default, fallback="gray")


def normalize_font_spec(font: Any) -> dict[str, str] | None:
    if isinstance(font, str):
        family = font.strip()
        return {"family": family, "path": ""} if family else None

    if isinstance(font, dict):
        family = str(font.get("family", "")).strip()
        path = str(font.get("path", "")).strip()
        if family or path:
            return {"family": family, "path": path}

    return None


def colormap_to_uint8(normalized: np.ndarray, colormap: Any = "gray") -> np.ndarray:
    normalized = np.asarray(normalized, dtype=np.float64)
    spec = normalize_colormap_spec(colormap, fallback="gray")

    if spec == "gray":
        grey = np.rint(normalized * 255.0).astype(np.uint8)
        rgb = np.empty(grey.shape + (3,), dtype=np.uint8)
        rgb[..., 0] = grey
        rgb[..., 1] = grey
        rgb[..., 2] = grey
        return rgb

    if isinstance(spec, dict) and spec.get("mode") == "custom":
        stops = spec["stops"]
        positions = np.array([float(stop["position"]) for stop in stops], dtype=np.float64)
        colors = np.array([_hex_to_rgb01(str(stop["color"])) for stop in stops], dtype=np.float64)
        flat = normalized.reshape(-1)
        rgb = np.empty((flat.shape[0], 3), dtype=np.uint8)
        for channel in range(3):
            rgb[:, channel] = np.rint(np.interp(flat, positions, colors[:, channel]) * 255.0).astype(np.uint8)
        return rgb.reshape(normalized.shape + (3,))

    cmap_name = spec["preset"] if isinstance(spec, dict) else spec
    cmap = _get_colormap(cmap_name)
    rgba = cmap(normalized)
    return (rgba[:, :, :3] * 255).astype(np.uint8)

@dataclass
class DataField:
    data: np.ndarray        # shape (yres, xres), dtype float64
    xres: int = 0
    yres: int = 0
    xreal: float = 1e-6    # physical width in metres
    yreal: float = 1e-6    # physical height in metres
    xoff: float = 0.0
    yoff: float = 0.0
    si_unit_xy: str = "m"
    si_unit_z: str = "m"
    domain: str = "spatial"  # "spatial" or "frequency"
    colormap: str | dict[str, Any] = "viridis"
    display_offset: float = 0.0
    display_scale: float = 1.0
    overlays: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 2:
            raise ValueError(f"DataField.data must be 2-D, got shape {self.data.shape}")
        self.yres, self.xres = self.data.shape
        self.overlays = deepcopy(self.overlays) if isinstance(self.overlays, list) else []

    def copy(self) -> "DataField":
        """Return a deep copy with independent data array."""
        return DataField(
            data=self.data.copy(),
            xres=self.xres,
            yres=self.yres,
            xreal=self.xreal,
            yreal=self.yreal,
            xoff=self.xoff,
            yoff=self.yoff,
            si_unit_xy=self.si_unit_xy,
            si_unit_z=self.si_unit_z,
            domain=self.domain,
            colormap=self.colormap,
            display_offset=self.display_offset,
            display_scale=self.display_scale,
            overlays=deepcopy(self.overlays),
        )

    def replace(self, **kwargs) -> "DataField":
        """Return a copy with selected fields replaced. data is deep-copied unless provided."""
        base = {
            "data": self.data.copy(),
            "xres": self.xres,
            "yres": self.yres,
            "xreal": self.xreal,
            "yreal": self.yreal,
            "xoff": self.xoff,
            "yoff": self.yoff,
            "si_unit_xy": self.si_unit_xy,
            "si_unit_z": self.si_unit_z,
            "domain": self.domain,
            "colormap": self.colormap,
            "display_offset": self.display_offset,
            "display_scale": self.display_scale,
            "overlays": deepcopy(self.overlays),
        }
        base.update(kwargs)
        return DataField(**base)

    @property
    def dx(self) -> float:
        """Physical pixel size in x (metres)."""
        return self.xreal / self.xres if self.xres else 1.0

    @property
    def dy(self) -> float:
        """Physical pixel size in y (metres)."""
        return self.yreal / self.yres if self.yres else 1.0


# ---------------------------------------------------------------------------
# Utility helpers shared across nodes
# ---------------------------------------------------------------------------

def normalize_for_colormap(
    data: np.ndarray,
    *,
    offset: float = 0.0,
    scale: float = 1.0,
    data_min: float | None = None,
    data_max: float | None = None,
) -> np.ndarray:
    """
    Normalize an array to [0, 1] for colormap lookup, then apply a display window.

    offset/scale operate in normalized data coordinates:
      output = clip((base_norm - offset) / scale, 0, 1)
    So offset=0, scale=1 maps the full data range 1:1 into the colormap.
    """
    data = np.asarray(data, dtype=np.float64)
    dmin = float(data.min()) if data_min is None else float(data_min)
    dmax = float(data.max()) if data_max is None else float(data_max)

    if dmax > dmin:
        base_norm = (data - dmin) / (dmax - dmin)
    else:
        base_norm = np.zeros_like(data)

    offset = float(offset)
    scale = float(scale)
    if not np.isfinite(offset):
        offset = 0.0
    if not np.isfinite(scale) or scale <= 0.0:
        scale = 1.0

    return np.clip((base_norm - offset) / scale, 0.0, 1.0)


def datafield_to_uint8(df: DataField, colormap: Any = "gray") -> np.ndarray:
    """
    Normalize a DataField to a uint8 (H, W, 3) RGB array using matplotlib colormap.
    Returns shape (H, W, 3) uint8.
    """
    normalized = normalize_for_colormap(
        df.data,
        offset=df.display_offset,
        scale=df.display_scale,
    )
    return colormap_to_uint8(normalized, colormap)


_SI_PREFIXES = [
    (1e24, "Y"),
    (1e21, "Z"),
    (1e18, "E"),
    (1e15, "P"),
    (1e12, "T"),
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "u"),
    (1e-9, "n"),
    (1e-12, "p"),
    (1e-15, "f"),
    (1e-18, "a"),
    (1e-21, "z"),
    (1e-24, "y"),
]
_PREFIXABLE_UNITS = {"m", "s", "A", "V", "W", "Hz", "F", "C", "J", "N", "Pa", "T", "H", "S", "g", "K", "Ohm", "ohm", "Ω"}


def _format_numeric(value: float) -> str:
    if not np.isfinite(value):
        return str(value)
    abs_value = abs(value)
    if abs_value == 0:
        return "0"
    if abs_value >= 1e4 or abs_value < 1e-3:
        return f"{value:.3e}"
    return f"{value:.4g}"


def _format_with_unit(value: float, unit: str) -> str:
    unit = (unit or "").strip()
    if not unit:
        return _format_numeric(value)
    if unit in _PREFIXABLE_UNITS and np.isfinite(value) and value != 0:
        abs_value = abs(value)
        for scale, prefix in _SI_PREFIXES:
            scaled = abs_value / scale
            if 1 <= scaled < 1000:
                signed = value / scale
                return f"{_format_numeric(signed)} {prefix}{unit}"
    return f"{_format_numeric(value)} {unit}"


def _nice_length(target: float) -> float:
    if not np.isfinite(target) or target <= 0:
        return 0.0
    exponent = np.floor(np.log10(target))
    base = 10.0 ** exponent
    for step in (5.0, 2.0, 1.0):
        candidate = step * base
        if candidate <= target:
            return candidate
    return base


def _display_value_range(field: DataField) -> tuple[float, float, float]:
    data = np.asarray(field.data, dtype=np.float64)
    dmin = float(data.min())
    dmax = float(data.max())
    if not np.isfinite(dmin) or not np.isfinite(dmax) or dmax <= dmin:
        return dmin, dmin, dmin

    offset = float(field.display_offset)
    scale = float(field.display_scale)
    if not np.isfinite(offset):
        offset = 0.0
    if not np.isfinite(scale) or scale <= 0.0:
        scale = 1.0

    low_norm = float(np.clip(offset, 0.0, 1.0))
    high_norm = float(np.clip(offset + scale, 0.0, 1.0))
    if high_norm < low_norm:
        low_norm, high_norm = high_norm, low_norm
    mid_norm = 0.5 * (low_norm + high_norm)

    span = dmax - dmin
    return (
        dmin + low_norm * span,
        dmin + mid_norm * span,
        dmin + high_norm * span,
    )


def _normalize_font_match_key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _render_overlay_text(
    text: str,
    size_px: int,
    color: tuple[int, int, int],
    font_spec: Any = None,
):
    from PIL import Image, ImageDraw, ImageFont

    size_px = max(8, int(round(size_px)))
    font = _load_overlay_font(size_px, ImageFont, font_spec=font_spec)
    if font is not None:
        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        bbox = probe_draw.textbbox((0, 0), text, font=font)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        text_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)
        text_draw.text((-bbox[0], -bbox[1]), text, font=font, fill=(*color, 255))
        return text_image

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
    # Preserve edge sharpness if we ever have to scale the bitmap fallback font.
    scaled_mask = mask.resize((scaled_width, scaled_height), resample=resampling.NEAREST)
    text_image = Image.new("RGBA", (scaled_width, scaled_height), (*color, 0))
    text_image.putalpha(scaled_mask)
    return text_image


@lru_cache(maxsize=1)
def _overlay_font_candidates() -> tuple[str, ...]:
    candidates: list[str] = []

    try:
        import PIL

        pil_dir = Path(PIL.__file__).resolve().parent
        candidates.extend([
            str(pil_dir / "fonts" / "DejaVuSans.ttf"),
            str(pil_dir / "Tests" / "fonts" / "DejaVuSans.ttf"),
        ])
    except Exception:
        pass

    candidates.extend([
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])

    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique and Path(candidate).exists():
            unique.append(candidate)
    return tuple(unique)


def list_overlay_font_choices() -> tuple[str, ...]:
    labels: list[str] = []
    for candidate in _overlay_font_candidates():
        label = Path(candidate).stem
        if label and label not in labels:
            labels.append(label)
    return tuple(labels)


def _matching_overlay_font_candidates(family: str) -> list[str]:
    key = _normalize_font_match_key(family)
    if not key:
        return []

    matches: list[str] = []
    for candidate in _overlay_font_candidates():
        stem_key = _normalize_font_match_key(Path(candidate).stem)
        if key == stem_key or key in stem_key or stem_key in key:
            matches.append(candidate)
    return matches


def _load_overlay_font(size_px: int, image_font_module, font_spec: Any = None) -> Any:
    normalized = normalize_font_spec(font_spec)

    if normalized is not None:
        requested_path = normalized.get("path", "")
        requested_family = normalized.get("family", "")

        if requested_path:
            try:
                return image_font_module.truetype(requested_path, size_px)
            except Exception:
                pass

        if requested_family:
            try:
                return image_font_module.truetype(requested_family, size_px)
            except Exception:
                pass

            for candidate in _matching_overlay_font_candidates(requested_family):
                try:
                    return image_font_module.truetype(candidate, size_px)
                except Exception:
                    continue

    for candidate in _overlay_font_candidates():
        try:
            return image_font_module.truetype(candidate, size_px)
        except Exception:
            continue

    try:
        return image_font_module.truetype("DejaVuSans.ttf", size_px)
    except Exception:
        return None


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


def _draw_arrow(draw, start: tuple[float, float], end: tuple[float, float], color: str, width: int):
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
    left = (shaft_end[0] + px * head_width / 2.0, shaft_end[1] + py * head_width / 2.0)
    right = (shaft_end[0] - px * head_width / 2.0, shaft_end[1] - py * head_width / 2.0)
    draw.polygon([end, left, right], fill=color)


def _preview_markup_stroke_width(width: int, image_width: int, image_height: int) -> int:
    width = max(1, int(width))
    longest_dim = max(1, int(image_width), int(image_height))
    scale = max(1.0, longest_dim / float(PREVIEW_MARKUP_REFERENCE_DIM))
    return max(1, int(round(width * scale)))


def _sanitize_markup_shapes(shapes: Any) -> list[dict[str, Any]]:
    if not isinstance(shapes, list):
        return []

    parsed = []
    for shape in shapes:
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
        if not all(np.isfinite(value) for value in (x1, y1, x2, y2)):
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


def _apply_annotation_overlay(
    image: np.ndarray,
    field: DataField,
    colormap: Any,
    spec: dict[str, Any],
) -> np.ndarray:
    from PIL import Image, ImageDraw

    show_scale_bar = bool(spec.get("show_scale_bar", True))
    show_color_map = bool(spec.get("show_color_map", True))
    text_size = float(spec.get("text_size", 14.0))
    text_size = float(np.clip(text_size, 6.0, 96.0)) if np.isfinite(text_size) else 14.0
    font_spec = normalize_font_spec(spec.get("font"))

    current = np.asarray(image, dtype=np.uint8)
    if current.ndim == 2:
        current = np.repeat(current[:, :, np.newaxis], 3, axis=2)

    height, current_width = current.shape[:2]
    field_width = max(1, int(field.xres))
    legend_width = max(72, int(round(field_width * 0.18))) if show_color_map else 0
    canvas_width = current_width + legend_width
    canvas = np.full((height, canvas_width, 3), 255, dtype=np.uint8)
    canvas[:, :current_width] = current

    pil_image = Image.fromarray(canvas)
    draw = ImageDraw.Draw(pil_image)
    base_font_px = max(6, int(round(text_size)))

    if show_scale_bar and field_width > 0 and np.isfinite(field.xreal) and field.xreal > 0:
        target_real = field.xreal / 5.0
        bar_real = _nice_length(target_real)
        if bar_real > 0 and np.isfinite(field.dx) and field.dx > 0:
            bar_px = max(1, int(round(bar_real / field.dx)))
            margin_x = max(8, field_width // 24)
            margin_y = max(8, height // 24)
            bar_height = max(3, int(round(height * 0.012)))
            bar_px = min(bar_px, max(1, field_width - 2 * margin_x))
            x0 = margin_x
            x1 = x0 + bar_px
            y1 = height - margin_y
            y0 = y1 - bar_height
            text = _format_with_unit(bar_real, field.si_unit_xy)
            text_image = _render_overlay_text(text, base_font_px, (255, 255, 255), font_spec=font_spec)
            text_w, text_h = text_image.size
            label_pad = 2
            bg_left = max(0, x0 - 4)
            bg_top = max(0, y0 - text_h - label_pad * 3)
            bg_right = min(canvas_width, max(x1 + 4, x0 + text_w + 8))
            bg_bottom = min(height, y1 + 4)
            draw.rectangle((bg_left, bg_top, bg_right, bg_bottom), fill=(0, 0, 0))
            draw.rectangle((x0, y0, x1, y1), fill=(255, 255, 255))
            pil_image.paste(text_image, (x0, bg_top + label_pad), text_image)

    if show_color_map and legend_width > 0:
        panel_x0 = current_width
        draw.rectangle((panel_x0, 0, canvas_width, height), fill=(245, 245, 245))
        grad_x0 = panel_x0 + max(8, legend_width // 7)
        grad_w = max(12, legend_width // 5)
        grad_y0 = max(10, height // 18)
        grad_y1 = max(grad_y0 + 10, height - grad_y0)
        grad_h = grad_y1 - grad_y0
        gradient = np.linspace(1.0, 0.0, grad_h, dtype=np.float64)[:, np.newaxis]
        gradient = np.repeat(gradient, grad_w, axis=1)
        gradient_rgb = colormap_to_uint8(gradient, colormap)
        pil_image.paste(Image.fromarray(gradient_rgb), (grad_x0, grad_y0))
        draw.rectangle((grad_x0, grad_y0, grad_x0 + grad_w, grad_y1), outline=(40, 40, 40), width=1)

        legend_min, legend_mid, legend_max = _display_value_range(field)
        labels = [
            (legend_max, grad_y0),
            (legend_mid, grad_y0 + grad_h // 2),
            (legend_min, grad_y1),
        ]
        text_x = grad_x0 + grad_w + 8
        for value, y_center in labels:
            text_image = _render_overlay_text(
                _format_with_unit(value, field.si_unit_z),
                base_font_px,
                (20, 20, 20),
                font_spec=font_spec,
            )
            text_y = int(round(y_center - text_image.size[1] / 2))
            text_y = max(0, min(height - text_image.size[1], text_y))
            pil_image.paste(text_image, (text_x, text_y), text_image)

    return np.asarray(pil_image, dtype=np.uint8)


def _apply_markup_overlay(image: np.ndarray, field: DataField, spec: dict[str, Any]) -> np.ndarray:
    from PIL import Image, ImageDraw

    current = np.asarray(image, dtype=np.uint8)
    if current.ndim == 2:
        current = np.repeat(current[:, :, np.newaxis], 3, axis=2)

    pil_image = Image.fromarray(current.copy())
    draw = ImageDraw.Draw(pil_image)
    field_width = max(1, int(field.xres))
    field_height = max(1, int(field.yres))

    for shape in _sanitize_markup_shapes(spec.get("shapes")):
        x1 = float(shape["x1"]) * field_width
        y1 = float(shape["y1"]) * field_height
        x2 = float(shape["x2"]) * field_width
        y2 = float(shape["y2"]) * field_height
        color = str(shape["color"])
        stroke_width = _preview_markup_stroke_width(int(shape["width"]), field_width, field_height)
        kind = str(shape["kind"])

        if kind == "line":
            draw.line(((x1, y1), (x2, y2)), fill=color, width=stroke_width)
        elif kind == "rectangle":
            draw.rectangle((x1, y1, x2, y2), outline=color, width=stroke_width)
        elif kind == "circle":
            draw.ellipse((x1, y1, x2, y2), outline=color, width=stroke_width)
        elif kind == "arrow":
            _draw_arrow(draw, (x1, y1), (x2, y2), color, stroke_width)

    return np.asarray(pil_image, dtype=np.uint8)


def render_datafield_preview(df: DataField, colormap: Any = "gray") -> np.ndarray:
    current = datafield_to_uint8(df, colormap)
    for overlay in df.overlays:
        if not isinstance(overlay, dict):
            continue
        kind = str(overlay.get("kind", "")).strip().lower()
        if kind == "annotation":
            current = _apply_annotation_overlay(current, df, colormap, overlay)
        elif kind == "markup":
            current = _apply_markup_overlay(current, df, overlay)
    return current


def image_to_uint8(image: np.ndarray) -> np.ndarray:
    """
    Convert an IMAGE (float or uint8, 2-D or 3-D) to uint8 (H,W,3) or (H,W) for PIL.
    """
    if image.dtype == np.uint8:
        return image
    # float — normalize to [0, 255]
    imin, imax = image.min(), image.max()
    if imax > imin:
        out = (image - imin) / (imax - imin) * 255.0
    else:
        out = np.zeros_like(image)
    return out.astype(np.uint8)


def encode_preview(arr: np.ndarray) -> str:
    """
    Encode a uint8 numpy array as a base64 data URI (PNG).
    arr: (H, W) grayscale or (H, W, 3) RGB, uint8.
    """
    import base64
    import io
    from PIL import Image

    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=1, optimize=False)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


@lru_cache(maxsize=len(COLORMAPS))
def _get_colormap(colormap: str):
    from matplotlib import colormaps
    return colormaps[colormap]
