from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from backend.node_registry import register_node
from backend.execution_context import emit_warning
from backend.data_types import DataField, LineData, MeshModel, datafield_to_uint8, image_to_uint8


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
                "directory_path": ("FOLDER_PICKER", {
                    "default": "",
                    "label": "directory",
                    "placement": "top",
                    "hide_when_input_connected": "directory",
                    "top_socket_input": "directory",
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
                        "LINE": ["CSV", "NPZ", "JSON"],
                        "RECORD_TABLE": ["CSV", "JSON"],
                        "DATA_TABLE": ["CSV", "JSON"],
                        "FLOAT": ["TXT", "JSON"],
                        "MESH_MODEL": ["OBJ", "STL"],
                    },
                    "source_type_input": "value",
                }),
            },
            "optional": {
                "directory": ("DIRECTORY", {"label": "directory"}),
            },
        }

    OUTPUTS = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save a single graph value to disk. Supports fields, images, lines, tables, scalars, and 3D meshes."
    )

    _broadcast_warning_fn = None
    _current_node_id = None

    def save(
        self,
        filename: str,
        directory_path: str,
        format: str,
        value,
        directory: str | None = None,
    ):
        path = self._resolve_save_path(filename, format, directory, directory_path)

        if isinstance(value, MeshModel):
            self._save_mesh(path, value, format)
        elif isinstance(value, DataField):
            self._save_datafield(path, value, format)
        elif isinstance(value, np.ndarray):
            if value.ndim == 1:
                self._save_line(path, LineData(data=value), format)
            else:
                self._save_image_or_array(path, value, format)
        elif isinstance(value, LineData):
            self._save_line(path, value, format)
        elif isinstance(value, list):
            self._save_table(path, value, format)
        elif isinstance(value, (int, float, np.floating, np.integer)):
            self._save_scalar(path, float(value), format)
        else:
            raise ValueError(f"Save does not support input type: {type(value).__name__}")

        self._send_warning(f"Saved to {path.name}")
        return ()

    def _resolve_save_path(
        self,
        filename: str,
        format_name: str,
        directory: str | None,
        directory_path: str = "",
    ) -> Path:
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
        raw_directory = str(directory).strip() if directory is not None else ""
        if not raw_directory:
            raw_directory = str(directory_path).strip() if directory_path is not None else ""

        if not raw_filename:
            raise ValueError("No output filename selected — enter a file name.")

        if raw_directory:
            dir_path = Path(raw_directory).expanduser()
            if dir_path.exists() and not dir_path.is_dir():
                raise ValueError("Directory input expects a folder path, not a file path.")
            if not dir_path.exists():
                if dir_path.suffix:
                    raise ValueError("Directory input expects a folder path, not a file path.")
                dir_path.mkdir(parents=True, exist_ok=True)
            path = dir_path / Path(raw_filename).name
        else:
            path = Path(raw_filename).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        return path

    def _save_datafield(self, path: Path, field: DataField, format_name: str):
        if format_name == "TIFF":
            import tifffile
            tifffile.imwrite(str(path), np.asarray(field.data, dtype=np.float32))
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

    def _save_line(self, path: Path, line: LineData, format_name: str):
        y = np.asarray(line.data, dtype=np.float64).ravel()
        x = np.asarray(line.x_axis, dtype=np.float64).ravel()[: len(y)] if line.x_axis is not None else np.arange(len(y), dtype=np.float64)
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

    def _send_warning(self, message: str):
        emit_warning(message)
