"""
Display / output nodes.

Preview accepts both DATA_FIELD and IMAGE via optional inputs —
connect whichever type you have. The server injects _broadcast_fn
before execution begins.
"""

from __future__ import annotations
import json
import numpy as np
from backend.node_registry import register_node
from backend.data_types import (
    DataField,
    MeasureTable,
    COLORMAPS,
    CUSTOM_FILE_FONT,
    DEFAULT_CUSTOM_COLORMAP_STOPS,
    SYSTEM_DEFAULT_FONT,
    colormap_to_uint8,
    datafield_to_uint8,
    encode_preview,
    image_to_uint8,
    list_overlay_font_choices,
    normalize_colormap_spec,
    normalize_font_spec,
    normalize_for_colormap,
    render_datafield_preview,
    resolve_colormap_input,
)


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


def _scalar_payload(value: float, unit: str = "") -> dict:
    payload = {"value": float(value)}
    if isinstance(unit, str) and unit.strip():
        payload["unit"] = unit.strip()
    return payload


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


def _parse_markup_shapes(raw_shapes: str | list | None) -> list[dict[str, object]]:
    if isinstance(raw_shapes, str):
        try:
            raw_shapes = json.loads(raw_shapes or "[]")
        except json.JSONDecodeError:
            raw_shapes = []

    if not isinstance(raw_shapes, list):
        return []

    parsed: list[dict[str, object]] = []
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
    left = (
        shaft_end[0] + px * head_width / 2.0,
        shaft_end[1] + py * head_width / 2.0,
    )
    right = (
        shaft_end[0] - px * head_width / 2.0,
        shaft_end[1] - py * head_width / 2.0,
    )
    draw.polygon([end, left, right], fill=color)


def _render_markup_image(image: np.ndarray, shapes: list[dict[str, object]]) -> np.ndarray:
    from PIL import Image, ImageDraw

    base = image_to_uint8(image)
    if base.ndim == 2:
        base = np.repeat(base[:, :, np.newaxis], 3, axis=2)

    canvas = Image.fromarray(base.copy())
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


@register_node(display_name="Color Map")
class ColorMap:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["preset", "custom"], {"default": "preset"}),
                "preset": (list(COLORMAPS), {
                    "default": "viridis",
                    "show_when_widget_value": {"mode": ["preset"]},
                }),
                "stops": ("STRING", {
                    "default": json.dumps(list(DEFAULT_CUSTOM_COLORMAP_STOPS)),
                    "colormap_stops": True,
                    "show_when_widget_value": {"mode": ["custom"]},
                }),
            }
        }

    RETURN_TYPES = ("COLORMAP",)
    RETURN_NAMES = ("colormap",)
    FUNCTION = "build"
    CATEGORY = "display"
    DESCRIPTION = (
        "Build a reusable colormap. Choose a preset, or create a custom gradient with min/max colours "
        "and any number of intermediate stops."
    )

    def build(self, mode: str, preset: str, stops: str | None = None, stops_json: str | None = None) -> tuple:
        if mode == "preset":
            return ({"mode": "preset", "preset": normalize_colormap_spec(preset)},)

        try:
            raw_stops = stops if stops is not None else stops_json
            stops_data = json.loads(raw_stops or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Custom colormap stops must be valid JSON.") from exc

        spec = normalize_colormap_spec({"mode": "custom", "stops": stops_data}, fallback=None)
        if not (isinstance(spec, dict) and spec.get("mode") == "custom"):
            raise ValueError("Custom colormap must include at least min and max colours.")
        return (spec,)


@register_node(display_name="Font")
class Font:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "family": ([SYSTEM_DEFAULT_FONT, *list_overlay_font_choices(), CUSTOM_FILE_FONT], {
                    "default": SYSTEM_DEFAULT_FONT,
                }),
                "font_file": ("FILE_PICKER", {
                    "default": "",
                    "show_when_widget_value": {"family": [CUSTOM_FILE_FONT]},
                }),
            }
        }

    RETURN_TYPES = ("FONT",)
    RETURN_NAMES = ("font",)
    FUNCTION = "build"
    CATEGORY = "display"
    DESCRIPTION = (
        "Build a reusable font spec for annotation overlays. Choose a discovered system font, "
        "use the default fallback stack, or point to a custom font file."
    )

    def build(self, family: str, font_file: str = "") -> tuple:
        if family == SYSTEM_DEFAULT_FONT:
            return (None,)
        if family == CUSTOM_FILE_FONT:
            return (normalize_font_spec({"path": font_file}),)
        return (normalize_font_spec({"family": family}),)


@register_node(display_name="Annotations")
class Annotations:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "colormap": (["auto"] + list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
                "show_scale_bar": ("BOOLEAN", {"default": True}),
                "show_color_map": ("BOOLEAN", {"default": True}),
                "text_size": ("FLOAT", {
                    "default": 14.0,
                    "min": 6.0,
                    "max": 96.0,
                    "step": 1.0,
                }),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
                "font": ("FONT",),
            },
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("annotated",)
    FUNCTION = "render"
    CATEGORY = "display"
    DESCRIPTION = (
        "Attach optional publication-style annotations to a DATA_FIELD without flattening the raw data. "
        "The preview shows a scale bar and/or side colour legend, while downstream field operations keep the underlying AFM values."
    )

    def render(
        self,
        field: DataField,
        colormap: str,
        show_scale_bar: bool,
        show_color_map: bool,
        text_size: float = 1.0,
        colormap_map=None,
        font=None,
    ) -> tuple:
        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=field.colormap,
            default="gray",
        )
        text_size = float(np.clip(text_size, 6.0, 96.0)) if np.isfinite(text_size) else 14.0
        out = field.replace(
            colormap=resolved_colormap,
            overlays=[
                *field.overlays,
                {
                    "kind": "annotation",
                    "show_scale_bar": bool(show_scale_bar),
                    "show_color_map": bool(show_color_map),
                    "text_size": text_size,
                    "font": normalize_font_spec(font),
                },
            ],
        )
        return (out,)


@register_node(display_name="Markup")
class Markup:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shape": (["line", "rectangle", "circle", "arrow"], {"default": "line"}),
                "stroke_color": ("STRING", {"default": "#ffd54f", "color_picker": True}),
                "stroke_width": ("INT", {"default": 3, "min": 1, "max": 64, "step": 1}),
                "clear_shapes": ("BUTTON", {"label": "Clear Shapes", "set_widgets": {"markup_shapes": "[]"}}),
                "markup_shapes": ("STRING", {"default": "[]", "hidden": True}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("annotated",)
    FUNCTION = "process"
    CATEGORY = "display"
    DESCRIPTION = (
        "Draw simple vector markup over a DATA_FIELD without flattening the underlying data. "
        "Choose a shape mode, colour, and stroke width, then drag directly on the preview to place lines, rectangles, circles, or arrows."
    )

    _broadcast_overlay_fn = None
    _current_node_id: str = ""

    def process(
        self,
        field: DataField,
        shape: str,
        stroke_color: str,
        stroke_width: int,
        markup_shapes: str,
    ) -> tuple:
        shapes = _parse_markup_shapes(markup_shapes)
        out = field.replace(
            overlays=[
                *field.overlays,
                {
                    "kind": "markup",
                    "shapes": shapes,
                },
            ],
        )

        if Markup._broadcast_overlay_fn is not None:
            Markup._broadcast_overlay_fn(
                Markup._current_node_id,
                {
                    "kind": "markup",
                    "section_title": "Markup",
                    "image": encode_preview(datafield_to_uint8(field, field.colormap)),
                    "shape": str(shape),
                    "stroke_color": _normalize_markup_color(stroke_color),
                    "stroke_width": max(1, int(stroke_width)),
                },
            )

        return (out,)


@register_node(display_name="Preview")
class PreviewImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "colormap": (["auto"] + list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
                "image": ("IMAGE",),
                "field": ("DATA_FIELD",),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "preview"
    CATEGORY = "display"
    OUTPUT_NODE = True
    DESCRIPTION = "Display an IMAGE or DATA_FIELD as a coloured thumbnail. Connect either input."

    _broadcast_fn = None
    _current_node_id: str = ""

    def preview(
        self,
        colormap: str,
        image: np.ndarray | None = None,
        field=None,
        colormap_map=None,
    ) -> tuple:
        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=field.colormap if field is not None else None,
            default="gray",
        )

        # Prefer field if both are connected; accept whichever is provided
        if field is not None:
            arr_u8 = render_datafield_preview(field, resolved_colormap)
        elif image is not None:
            arr_u8 = image_to_uint8(image)
            if arr_u8.ndim == 2:
                if image.dtype == np.uint8:
                    normalized = arr_u8.astype(np.float64) / 255.0
                else:
                    imin, imax = image.min(), image.max()
                    if imax > imin:
                        normalized = (image - imin) / (imax - imin)
                    else:
                        normalized = np.zeros_like(image, dtype=np.float64)
                arr_u8 = colormap_to_uint8(normalized, resolved_colormap)
        else:
            raise ValueError("Connect either an IMAGE or DATA_FIELD input to Preview.")

        data_uri = encode_preview(arr_u8)

        if PreviewImage._broadcast_fn is not None:
            PreviewImage._broadcast_fn(PreviewImage._current_node_id, data_uri)

        return ()


@register_node(display_name="3D View")
class View3D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "colormap": (["auto"] + list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
                "z_scale": ("FLOAT", {"default": 1, "min": 0.1, "max": 10.0, "step": 0.05}),
                "resolution": ("INT", {"default": 128, "min": 32, "max": 512, "step": 16}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "render"
    CATEGORY = "display"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Interactive 3D surface view of a DATA_FIELD. "
        "Drag to rotate, scroll to zoom. z_scale exaggerates height."
    )

    _broadcast_mesh_fn = None
    _current_node_id: str = ""

    def render(
        self, field: DataField,
        colormap: str, z_scale: float, resolution: int, colormap_map=None,
    ) -> tuple:
        import base64

        data = field.data
        yres, xres = data.shape

        # Downsample if larger than resolution
        step_y = max(1, yres // resolution)
        step_x = max(1, xres // resolution)
        z = data[::step_y, ::step_x].astype(np.float32)
        ny, nx = z.shape

        # Normalize for colormap
        zmin, zmax = float(z.min()), float(z.max())
        z_norm = normalize_for_colormap(
            z,
            offset=field.display_offset,
            scale=field.display_scale,
            data_min=float(field.data.min()),
            data_max=float(field.data.max()),
        )

        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=field.colormap,
            default="gray",
        )
        colors_u8 = colormap_to_uint8(z_norm, resolved_colormap)

        # Base64-encode arrays for efficient WS transport
        z_b64 = base64.b64encode(z.tobytes()).decode()
        colors_b64 = base64.b64encode(colors_u8.tobytes()).decode()

        mesh_data = {
            "width": nx,
            "height": ny,
            "z_data": z_b64,
            "colors": colors_b64,
            "z_min": zmin,
            "z_max": zmax,
            "z_scale": float(z_scale * 0.1),
            "x_range": [float(field.xoff), float(field.xoff + field.xreal)],
            "y_range": [float(field.yoff), float(field.yoff + field.yreal)],
        }

        if View3D._broadcast_mesh_fn is not None:
            View3D._broadcast_mesh_fn(View3D._current_node_id, mesh_data)

        return ()


@register_node(display_name="Print Table")
class PrintTable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "table": ("ANY_TABLE",),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "print_table"
    CATEGORY = "display"
    OUTPUT_NODE = True
    DESCRIPTION = "Send a measurement or record table to the browser as a WebSocket message for display."

    _broadcast_table_fn = None
    _current_node_id: str = ""

    def print_table(self, table: list) -> tuple:
        if PrintTable._broadcast_table_fn is not None:
            PrintTable._broadcast_table_fn(PrintTable._current_node_id, table)
        return ()


@register_node(display_name="Value Display")
class ValueDisplay:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("VALUE_SOURCE",),
                "measurement": ("STRING", {
                    "default": "",
                    "choices_from_measure_input": "value",
                    "show_when_source_type": {
                        "value": ["MEASURE_TABLE"],
                    },
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "display_value"
    CATEGORY = "display"
    DESCRIPTION = "Display a FLOAT, or a selected numeric row from a measurement table, and pass the value through unchanged."

    _broadcast_value_fn = None
    _current_node_id: str = ""

    def display_value(self, value, measurement: str = "") -> tuple:
        unit = ""
        if isinstance(value, MeasureTable):
            row = _measurement_entry(value, measurement)
            numeric = _measurement_value(value, measurement)
            unit = row.get("unit", "") if isinstance(row.get("unit"), str) else ""
        else:
            numeric = float(value)
        if ValueDisplay._broadcast_value_fn is not None:
            ValueDisplay._broadcast_value_fn(ValueDisplay._current_node_id, _scalar_payload(numeric, unit))
        return (numeric,)
