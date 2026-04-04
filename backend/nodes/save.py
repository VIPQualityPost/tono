from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

import tempfile

from backend.node_registry import register_node
from backend.execution_context import emit_warning, emit_file_download
from backend.data_types import (
    DataField, LineData, MeshModel, datafield_to_uint8, image_to_uint8,
    _SI_PREFIXES, _PREFIXABLE_UNITS,
)

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "tono-downloads"

@register_node(display_name="Save")
class Save:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {
                    "default": "",
                    "placeholder": "filename",
                    "placement": "top",
                }),
                "value": ("DATA_FIELD", {
                    "label": "value",
                    "accepted_types": [
                        "IMAGE",
                        "ANNOTATION_SOURCE",
                        "LINE",
                        "RECORD_TABLE",
                        "DATA_TABLE",
                        "MESH_MODEL",
                        "FLOAT",
                    ],
                }),
                "format": ("STRING", {
                    "default": "TIFF",
                    "choices_by_source_type": {
                        "DATA_FIELD": ["TIFF", "PNG", "NPZ"],
                        "IMAGE": ["PNG", "TIFF", "NPZ"],
                        "ANNOTATION_SOURCE": ["PNG", "TIFF", "NPZ"],
                        "LINE": ["PNG", "TIFF", "CSV", "NPZ", "JSON"],
                        "RECORD_TABLE": ["CSV", "JSON"],
                        "DATA_TABLE": ["CSV", "JSON"],
                        "FLOAT": ["TXT", "JSON"],
                        "MESH_MODEL": ["OBJ", "STL"],
                    },
                    "source_type_input": "value",
                }),
            },
            "optional": {
                "plot_title": ("STRING", {
                    "default": "",
                    "placeholder": "plot title (optional)",
                    "label": "title",
                    "show_when_source_type": {"value": ["LINE"]},
                }),
            },
        }

    OUTPUTS = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save a single graph value to disk. Supports fields, images, lines, tables, scalars, and 3D meshes."
    )

    def save(
        self,
        filename: str,
        format: str,
        value,
        plot_title: str = "",
    ):
        path = self._resolve_save_path(filename, format)

        if isinstance(value, MeshModel):
            self._save_mesh(path, value, format)
        elif isinstance(value, DataField):
            self._save_datafield(path, value, format)
        elif isinstance(value, np.ndarray):
            if value.ndim == 1:
                self._save_line(path, LineData(data=value), format, title=plot_title)
            else:
                self._save_image_or_array(path, value, format)
        elif isinstance(value, LineData):
            self._save_line(path, value, format, title=plot_title)
        elif isinstance(value, list):
            self._save_table(path, value, format)
        elif isinstance(value, (int, float, np.floating, np.integer)):
            self._save_scalar(path, float(value), format)
        else:
            raise ValueError(f"Save does not support input type: {type(value).__name__}")

        emit_warning(f"Saved to {path.name}")
        emit_file_download(str(path))
        return ()

    def _resolve_save_path(self, filename: str, format_name: str) -> Path:
        ext_map = {
            "PNG": ".png",
            "TIFF": ".tiff",
            "NPZ": ".npz",
            "CSV": ".csv",
            "JSON": ".json",
            "OBJ": ".obj",
            "STL": ".stl",
            "TXT": ".txt",
        }
        ext = ext_map[format_name]

        raw_filename = str(filename).strip() if filename is not None else ""
        if not raw_filename:
            raise ValueError("No output filename selected — enter a file name.")

        candidate = Path(raw_filename).expanduser()
        if candidate.is_absolute():
            candidate.parent.mkdir(parents=True, exist_ok=True)
            path = candidate
        else:
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            path = DOWNLOAD_DIR / candidate.name

        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        return path

    def _save_datafield(self, path: Path, field: DataField, format_name: str):
        if format_name == "TIFF":
            import tifffile
            tifffile.imwrite(str(path), datafield_to_uint8(field, field.colormap))
            return
        if format_name == "NPZ":
            np.savez(str(path), field=np.asarray(field.data))
            return
        if format_name == "PNG":
            from PIL import Image
            Image.fromarray(datafield_to_uint8(field, field.colormap)).save(str(path))
            return
        raise ValueError(f"Format {format_name} is not supported for DATA_FIELD.")

    def _save_image_or_array(self, path: Path, image: np.ndarray, format_name: str):
        arr = np.asarray(image)
        if format_name == "PNG":
            from PIL import Image
            Image.fromarray(image_to_uint8(arr)).save(str(path))
            return
        if format_name == "TIFF":
            import tifffile
            tifffile.imwrite(str(path), image_to_uint8(arr))
            return
        if format_name == "NPZ":
            np.savez(str(path), image=arr)
            return
        raise ValueError(f"Format {format_name} is not supported for IMAGE.")

    def _save_line(self, path: Path, line: LineData, format_name: str, title: str = ""):
        y = np.asarray(line.data, dtype=np.float64).ravel()
        x = np.asarray(line.x_axis, dtype=np.float64).ravel()[: len(y)] if line.x_axis is not None else np.arange(len(y), dtype=np.float64)
        if format_name in ("PNG", "TIFF"):
            self._save_line_plot(path, x, y, line.x_unit, line.y_unit, title, format_name)
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
            path.write_text(json.dumps({
                "x": x.tolist(),
                "y": y.tolist(),
                "x_unit": line.x_unit,
                "y_unit": line.y_unit,
            }, indent=2), encoding="utf-8")
            return
        raise ValueError(f"Format {format_name} is not supported for LINE.")

    def _save_line_plot(
        self,
        path: Path,
        x: np.ndarray,
        y: np.ndarray,
        x_unit: str,
        y_unit: str,
        title: str,
        format_name: str,
    ):
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

        # Scale data into prefixed units
        x = x / x_scale
        y = y / y_scale
        xmin, xmax = xmin / x_scale, xmax / x_scale
        ymin, ymax = ymin / y_scale, ymax / y_scale

        if ymax == ymin:
            ymin, ymax = ymin - 1, ymax + 1
        if xmax == xmin:
            xmax = xmin + 1
        # Add 5% padding to y range
        ypad = (ymax - ymin) * 0.05
        ymin -= ypad
        ymax += ypad

        def to_px(xv: float, yv: float) -> tuple[float, float]:
            px = margin["left"] + (xv - xmin) / (xmax - xmin) * pw
            py = margin["top"] + (1.0 - (yv - ymin) / (ymax - ymin)) * ph
            return px, py

        # Grid lines (5 horizontal, 5 vertical)
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

        # Plot line
        n = len(y)
        step = max(1, n // pw)
        xs, ys = x[::step], y[::step]
        pts = [to_px(float(xs[i]), float(ys[i])) for i in range(len(xs))]
        if len(pts) > 1:
            draw.line(pts, fill=line_color, width=2)

        # Border
        draw.rectangle(
            [margin["left"], margin["top"], margin["left"] + pw, margin["top"] + ph],
            outline=(100, 100, 100), width=1,
        )
        draw.text((margin["left"] + pw // 2, h - 10), x_label, fill=text_color, font=font, anchor="mb")
        # Vertical y label — draw rotated
        y_label_img = Image.new("RGBA", (200, 20), (0, 0, 0, 0))
        y_draw = ImageDraw.Draw(y_label_img)
        y_draw.text((100, 10), y_label, fill=text_color, font=font, anchor="mm")
        y_label_img = y_label_img.rotate(90, expand=True)
        img.paste(y_label_img, (2, margin["top"] + ph // 2 - y_label_img.height // 2), y_label_img)

        # Title
        if title and title.strip():
            draw.text((w // 2, 10), title.strip(), fill=text_color, font=font_title, anchor="mt")

        ext = ".png" if format_name == "PNG" else ".tiff"
        img.save(str(path.with_suffix(ext)))

    def _save_table(self, path: Path, rows: list, format_name: str):
        if format_name == "JSON":
            path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            return
        if format_name == "CSV":
            columns: list[str] = []
            for row in rows:
                if isinstance(row, dict):
                    for key in row.keys():
                        if key not in columns:
                            columns.append(str(key))
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row if isinstance(row, dict) else {"value": row})
            return
        raise ValueError(f"Format {format_name} is not supported for table inputs.")

    def _save_scalar(self, path: Path, value: float, format_name: str):
        if format_name == "TXT":
            path.write_text(f"{value}\n", encoding="utf-8")
            return
        if format_name == "JSON":
            path.write_text(json.dumps({"value": value}, indent=2), encoding="utf-8")
            return
        raise ValueError(f"Format {format_name} is not supported for scalar values.")

    def _save_mesh(self, path: Path, mesh: MeshModel, format_name: str):
        if format_name == "OBJ":
            self._save_obj(path, mesh)
            return
        if format_name == "STL":
            self._save_stl(path, mesh)
            return
        raise ValueError(f"Format {format_name} is not supported for MESH_MODEL.")

    def _save_obj(self, path: Path, mesh: MeshModel):
        lines = []
        for vertex in mesh.vertices:
            lines.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")
        for face in mesh.faces:
            lines.append(f"f {int(face[0]) + 1} {int(face[1]) + 1} {int(face[2]) + 1}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _save_stl(self, path: Path, mesh: MeshModel):
        def normal(a, b, c):
            n = np.cross(b - a, c - a)
            length = float(np.linalg.norm(n))
            return n / length if length > 0 else np.array([0.0, 1.0, 0.0], dtype=np.float32)

        lines = ["solid tono"]
        vertices = np.asarray(mesh.vertices, dtype=np.float32)
        for face in np.asarray(mesh.faces, dtype=np.int32):
            a, b, c = vertices[int(face[0])], vertices[int(face[1])], vertices[int(face[2])]
            n = normal(a, b, c)
            lines.append(f"  facet normal {n[0]} {n[1]} {n[2]}")
            lines.append("    outer loop")
            lines.append(f"      vertex {a[0]} {a[1]} {a[2]}")
            lines.append(f"      vertex {b[0]} {b[1]} {b[2]}")
            lines.append(f"      vertex {c[0]} {c[1]} {c[2]}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append("endsolid tono")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
