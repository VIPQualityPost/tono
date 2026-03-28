from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_preview
from backend.data_types import (
    COLORMAPS,
    DataField,
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
                "input": ("ANNOTATION_SOURCE", {
                    "label": "Input",
                    "accepted_types": ["DATA_FIELD", "IMAGE"],
                }),
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            }
        }

    OUTPUTS = ()
    FUNCTION = "preview"

    OUTPUT_NODE = True
    DESCRIPTION = "Display an IMAGE or DATA_FIELD as a coloured thumbnail."

    _broadcast_fn = None
    _current_node_id: str = ""

    def preview(
        self,
        colormap: str,
        input=None,
        colormap_map=None,
    ) -> tuple:
        field = input if isinstance(input, DataField) else None
        image = None if field is not None else input

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
            raise ValueError("Connect an IMAGE or DATA_FIELD input to Preview.")

        data_uri = encode_preview(arr_u8)

        emit_preview(data_uri)

        return ()
