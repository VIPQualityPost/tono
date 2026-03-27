from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import (
    COLORMAPS,
    DataField,
    colormap_to_uint8,
    normalize_for_colormap,
    resolve_colormap_input,
)


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

        step_y = max(1, yres // resolution)
        step_x = max(1, xres // resolution)
        z = data[::step_y, ::step_x].astype(np.float32)
        ny, nx = z.shape

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
