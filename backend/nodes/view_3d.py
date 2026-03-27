from __future__ import annotations
import base64
import io
import numpy as np
from backend.node_registry import register_node
from backend.data_types import (
    COLORMAPS,
    DataField,
    ImageData,
    MeshModel,
    _annotation_context_from_field,
    colormap_to_uint8,
    normalize_for_colormap,
    resolve_colormap_input,
)


def _darken_colors(colors: np.ndarray, factor: float) -> np.ndarray:
    return np.clip(np.rint(colors.astype(np.float32) * factor), 0, 255).astype(np.uint8)


def _grid_triangle_indices(nx: int, ny: int, *, reverse: bool = False) -> list[list[int]]:
    faces: list[list[int]] = []
    for iy in range(ny - 1):
        for ix in range(nx - 1):
            a = iy * nx + ix
            b = a + 1
            c = a + nx
            d = c + 1
            if reverse:
                faces.append([a, b, c])
                faces.append([b, d, c])
            else:
                faces.append([a, c, b])
                faces.append([b, c, d])
    return faces


def _build_mesh_model(z: np.ndarray, colors_u8: np.ndarray, z_scale: float, make_solid: bool) -> MeshModel:
    ny, nx = z.shape
    zmin = float(z.min())
    zmax = float(z.max())
    z_range = zmax - zmin if zmax != zmin else 1.0

    top_vertices = np.empty((nx * ny, 3), dtype=np.float32)
    top_colors = colors_u8.reshape(-1, 3).astype(np.uint8)
    for iy in range(ny):
        py = iy / max(ny - 1, 1) - 0.5
        for ix in range(nx):
            idx = iy * nx + ix
            px = ix / max(nx - 1, 1) - 0.5
            pz = ((float(z[iy, ix]) - zmin) / z_range - 0.5) * z_scale
            top_vertices[idx] = (px, pz, py)

    faces = _grid_triangle_indices(nx, ny)
    if not make_solid:
        return MeshModel(vertices=top_vertices, faces=np.asarray(faces, dtype=np.int32), colors=top_colors)

    base_y = float(top_vertices[:, 1].min())
    bottom_vertices = top_vertices.copy()
    bottom_vertices[:, 1] = base_y
    bottom_colors = _darken_colors(top_colors, 0.35)

    vertices = np.vstack([top_vertices, bottom_vertices]).astype(np.float32)
    colors = np.vstack([top_colors, bottom_colors]).astype(np.uint8)

    bottom_offset = len(top_vertices)
    faces.extend([[a + bottom_offset, b + bottom_offset, c + bottom_offset] for a, b, c in _grid_triangle_indices(nx, ny, reverse=True)])

    def _add_wall(a: int, b: int):
        faces.append([a, a + bottom_offset, b])
        faces.append([b, a + bottom_offset, b + bottom_offset])

    for ix in range(nx - 1):
        _add_wall(ix, ix + 1)
        top_row = (ny - 1) * nx
        _add_wall(top_row + ix + 1, top_row + ix)
    for iy in range(ny - 1):
        _add_wall((iy + 1) * nx, iy * nx)
        _add_wall(iy * nx + (nx - 1), (iy + 1) * nx + (nx - 1))

    return MeshModel(vertices=vertices, faces=np.asarray(faces, dtype=np.int32), colors=colors)


@register_node(display_name="3D View")
class View3D:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD", {"label": "mesh"}),
                "colormap": (["auto"] + list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
                "z_scale": ("FLOAT", {"default": 1, "min": 0.1, "max": 10.0, "step": 0.05}),
                "resolution": ("INT", {"default": 128, "min": 32, "max": 512, "step": 16}),
                "make_solid": ("BOOLEAN", {"default": False}),
                "camera_azimuth": ("FLOAT", {"default": 0.0, "hidden": True}),
                "camera_polar": ("FLOAT", {"default": 1.1, "hidden": True}),
                "camera_distance": ("FLOAT", {"default": 1.8, "hidden": True}),
                "viewport_snapshot": ("STRING", {"default": "", "hidden": True}),
            },
            "optional": {
                "map_field": ("DATA_FIELD", {"label": "map"}),
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            },
        }

    RETURN_TYPES = ("MESH_MODEL", "IMAGE")
    RETURN_NAMES = ("mesh", "viewport")
    FUNCTION = "render"

    OUTPUT_NODE = True
    DESCRIPTION = (
        "Interactive 3D surface view of a DATA_FIELD. "
        "Use the mesh input for geometry and optionally a second map input for coloring. "
        "Drag to rotate, scroll to zoom. z_scale exaggerates height."
    )

    _broadcast_mesh_fn = None
    _current_node_id: str = ""

    def render(
        self, field: DataField,
        colormap: str, z_scale: float, resolution: int, make_solid: bool = False,
        camera_azimuth: float = 0.0, camera_polar: float = 1.1, camera_distance: float = 1.8,
        viewport_snapshot: str = "",
        map_field: DataField | None = None, colormap_map=None,
    ) -> tuple:
        from scipy.ndimage import map_coordinates

        data = field.data
        yres, xres = data.shape

        step_y = max(1, yres // resolution)
        step_x = max(1, xres // resolution)
        z = data[::step_y, ::step_x].astype(np.float32)
        ny, nx = z.shape

        zmin, zmax = float(z.min()), float(z.max())
        color_field = map_field if map_field is not None else field
        color_data = color_field.data

        if color_field is field and color_data.shape == z.shape:
            color_samples = z
        elif color_field is field:
            color_samples = color_data[::step_y, ::step_x].astype(np.float32)
        else:
            x_phys = np.linspace(field.xoff, field.xoff + field.xreal, nx, dtype=np.float64)
            y_phys = np.linspace(field.yoff, field.yoff + field.yreal, ny, dtype=np.float64)
            grid_y, grid_x = np.meshgrid(y_phys, x_phys, indexing="ij")

            map_x = np.clip(
                (grid_x - color_field.xoff) / max(color_field.xreal, 1e-12) * max(color_field.xres - 1, 0),
                0.0,
                max(color_field.xres - 1, 0),
            )
            map_y = np.clip(
                (grid_y - color_field.yoff) / max(color_field.yreal, 1e-12) * max(color_field.yres - 1, 0),
                0.0,
                max(color_field.yres - 1, 0),
            )
            color_samples = map_coordinates(
                color_data.astype(np.float64),
                [map_y, map_x],
                order=1,
                mode="nearest",
            ).astype(np.float32)

        z_norm = normalize_for_colormap(
            color_samples,
            offset=color_field.display_offset,
            scale=color_field.display_scale,
            data_min=float(color_field.data.min()),
            data_max=float(color_field.data.max()),
        )

        resolved_colormap = resolve_colormap_input(
            colormap,
            colormap_input=colormap_map,
            inherited=color_field.colormap,
            default="gray",
        )
        colors_u8 = colormap_to_uint8(z_norm, resolved_colormap)
        mesh_model = _build_mesh_model(z, colors_u8, float(z_scale * 0.1), bool(make_solid))

        z_b64 = base64.b64encode(z.tobytes()).decode()
        colors_b64 = base64.b64encode(colors_u8.tobytes()).decode()
        positions_b64 = base64.b64encode(np.asarray(mesh_model.vertices, dtype=np.float32).tobytes()).decode()
        indices_b64 = base64.b64encode(np.asarray(mesh_model.faces, dtype=np.uint32).tobytes()).decode()
        mesh_colors_b64 = None
        if mesh_model.colors is not None:
            mesh_colors_b64 = base64.b64encode(np.asarray(mesh_model.colors, dtype=np.uint8).tobytes()).decode()

        mesh_data = {
            "width": nx,
            "height": ny,
            "z_data": z_b64,
            "colors": colors_b64,
            "positions": positions_b64,
            "indices": indices_b64,
            "vertex_colors": mesh_colors_b64,
            "z_min": zmin,
            "z_max": zmax,
            "z_scale": float(z_scale * 0.1),
            "make_solid": bool(make_solid),
            "camera_azimuth": float(camera_azimuth),
            "camera_polar": float(camera_polar),
            "camera_distance": float(camera_distance),
            "x_range": [float(field.xoff), float(field.xoff + field.xreal)],
            "y_range": [float(field.yoff), float(field.yoff + field.yreal)],
        }

        if View3D._broadcast_mesh_fn is not None:
            View3D._broadcast_mesh_fn(View3D._current_node_id, mesh_data)

        annotation_context = _annotation_context_from_field(color_field, resolved_colormap)
        annotation_context["xreal"] = float(field.xreal)
        annotation_context["si_unit_xy"] = str(field.si_unit_xy)
        viewport_image = ImageData(
            self._decode_viewport_snapshot(viewport_snapshot),
            metadata={
                "annotation_context": annotation_context,
                "viewport_camera": {
                    "azimuth": float(camera_azimuth),
                    "polar": float(camera_polar),
                    "distance": float(camera_distance),
                },
            },
        )
        return (mesh_model, viewport_image)

    def _decode_viewport_snapshot(self, snapshot: str) -> np.ndarray:
        text = str(snapshot or "").strip()
        if not text.startswith("data:image/"):
            return np.zeros((1, 1, 3), dtype=np.uint8)

        try:
            header, payload = text.split(",", 1)
            raw = base64.b64decode(payload)
            from PIL import Image
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            return np.asarray(image, dtype=np.uint8)
        except Exception:
            return np.zeros((1, 1, 3), dtype=np.uint8)
