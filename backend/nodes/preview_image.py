from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import (
    COLORMAPS,
    colormap_to_uint8,
    encode_preview,
    image_to_uint8,
    render_datafield_preview,
    resolve_colormap_input,
)


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
