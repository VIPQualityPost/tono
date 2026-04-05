"""
Exporter for MESH_MODEL values (Wavefront OBJ, ASCII STL).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import MeshModel
from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("MESH_MODEL",)

FORMATS: dict[str, FormatSpec] = {
    "OBJ": FormatSpec(ext=".obj", round_trip=True, label="Wavefront OBJ"),
    "STL": FormatSpec(ext=".stl", round_trip=True, label="STL (ASCII)"),
}


def save(path: Path, value: MeshModel, format_name: str, **_opts) -> None:
    if format_name == "OBJ":
        _save_obj(path, value)
        return
    if format_name == "STL":
        _save_stl(path, value)
        return
    raise ValueError(f"Format {format_name!r} is not supported for MESH_MODEL.")


def _save_obj(path: Path, mesh: MeshModel) -> None:
    lines: list[str] = []
    for vertex in mesh.vertices:
        lines.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")
    for face in mesh.faces:
        lines.append(f"f {int(face[0]) + 1} {int(face[1]) + 1} {int(face[2]) + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_stl(path: Path, mesh: MeshModel) -> None:
    def normal(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
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
