"""
Display / output nodes.

Preview accepts both DATA_FIELD and IMAGE via optional inputs —
connect whichever type you have. The server injects _broadcast_fn
before execution begins.
"""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, datafield_to_uint8, image_to_uint8, encode_preview


@register_node(display_name="Preview")
class PreviewImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "colormap": (["gray", "hot", "jet", "viridis", "plasma", "inferno"],),
            },
            "optional": {
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

    def preview(self, colormap: str, image: np.ndarray | None = None, field=None) -> tuple:
        # Prefer field if both are connected; accept whichever is provided
        if field is not None:
            arr_u8 = datafield_to_uint8(field, colormap)
        elif image is not None:
            if image.dtype != np.uint8:
                imin, imax = image.min(), image.max()
                if imax > imin:
                    norm = (image - imin) / (imax - imin)
                else:
                    norm = np.zeros_like(image)
                arr_u8 = (norm * 255).astype(np.uint8)
            else:
                arr_u8 = image

            if arr_u8.ndim == 2 and colormap != "gray":
                import matplotlib.cm as cm
                cmap = cm.get_cmap(colormap)
                rgba = cmap(arr_u8.astype(np.float32) / 255.0)
                arr_u8 = (rgba[:, :, :3] * 255).astype(np.uint8)
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
                "colormap": (["viridis", "gray", "hot", "jet", "plasma", "inferno", "terrain"],),
                "z_scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 20.0, "step": 0.1}),
                "resolution": ("INT", {"default": 128, "min": 32, "max": 512, "step": 16}),
            }
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
        colormap: str, z_scale: float, resolution: int,
    ) -> tuple:
        import matplotlib.cm as cm
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
        if zmax > zmin:
            z_norm = (z - zmin) / (zmax - zmin)
        else:
            z_norm = np.zeros_like(z)

        cmap = cm.get_cmap(colormap)
        rgba = cmap(z_norm)  # (ny, nx, 4) float [0,1]
        colors_u8 = (rgba[:, :, :3] * 255).astype(np.uint8)

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
            "z_scale": float(z_scale),
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
                "table": ("TABLE",),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "print_table"
    CATEGORY = "display"
    OUTPUT_NODE = True
    DESCRIPTION = "Send a TABLE to the browser as a WebSocket message for display."

    _broadcast_table_fn = None
    _current_node_id: str = ""

    def print_table(self, table: list) -> tuple:
        if PrintTable._broadcast_table_fn is not None:
            PrintTable._broadcast_table_fn(PrintTable._current_node_id, table)
        return ()
