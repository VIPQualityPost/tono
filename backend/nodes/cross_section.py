from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.execution_context import emit_overlay
from backend.data_types import DataField, LineData, datafield_to_uint8, encode_preview
from backend.nodes.helpers import _extend_to_edges


@register_node(display_name="Cross Section")
class CrossSection:
    """Extract a 1-D height profile along an arbitrary line across the image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "x1": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "extend": (["none", "to_edges"],),
                "n_samples": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1}),
            },
            "optional": {
                "marker_pair": ("COORDPAIR", {"label": "marker pair"}),
            },
        }

    OUTPUTS = (
        ('LINE', 'profile'),
        ('COORDPAIR', 'marker_pair'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Extract a cross-section profile along a line between two points. "
        "Drag the markers on the image to set the line endpoints. "
        "Equivalent to gwy_data_field_get_profile."
    )

    def process(
        self, field: DataField,
        x1: float, y1: float, x2: float, y2: float,
        extend: str, n_samples: int,
        marker_pair=None,
    ) -> tuple:
        from scipy.ndimage import map_coordinates

        if marker_pair is not None:
            (x1, y1), (x2, y2) = marker_pair

        marker_x1, marker_y1 = float(x1), float(y1)
        marker_x2, marker_y2 = float(x2), float(y2)

        xres, yres = field.xres, field.yres

        if extend == "to_edges":
            x1, y1, x2, y2 = _extend_to_edges(
                float(x1), float(y1), float(x2), float(y2),
            )

        px1, py1 = float(x1) * (xres - 1), float(y1) * (yres - 1)
        px2, py2 = float(x2) * (xres - 1), float(y2) * (yres - 1)

        line_len_px = np.hypot(px2 - px1, py2 - py1)
        if n_samples <= 0:
            n_samples = max(2, int(np.ceil(line_len_px)))

        t = np.linspace(0, 1, n_samples)
        coords_y = py1 + t * (py2 - py1)
        coords_x = px1 + t * (px2 - px1)

        profile = map_coordinates(field.data, [coords_y, coords_x], order=3, mode="nearest")

        image_uri = encode_preview(datafield_to_uint8(field, field.colormap))
        emit_overlay({
            "image": image_uri,
            "x1": marker_x1, "y1": marker_y1,
            "x2": marker_x2, "y2": marker_y2,
            "a_locked": marker_pair is not None,
            "b_locked": marker_pair is not None,
        })

        dx_real = (x2 - x1) * field.xreal
        dy_real = (y2 - y1) * field.yreal
        distance_axis = np.linspace(0.0, float(np.hypot(dx_real, dy_real)), n_samples, dtype=np.float64)

        return (
            LineData(
                data=profile.astype(np.float64),
                x_axis=distance_axis,
                x_unit=field.si_unit_xy,
                y_unit=field.si_unit_z,
            ),
            ((marker_x1, marker_y1), (marker_x2, marker_y2)),
        )
