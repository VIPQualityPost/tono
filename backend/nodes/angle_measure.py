from __future__ import annotations

import numpy as np

from backend.data_types import (
    DataField,
    ImageData,
    MeasureTable,
    _apply_angle_measure_overlay,
    encode_preview,
    image_metadata,
    image_to_uint8,
    render_datafield_preview,
)
from backend.execution_context import emit_overlay, emit_table
from backend.node_registry import register_node
from backend.nodes.helpers import _normalize_markup_color


def _clamp01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _sanitize_line_thickness(value: float | None, default: float = 1.35) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    if not np.isfinite(numeric):
        numeric = default
    return float(np.clip(numeric, 0.35, 6.0))


def _angle_metrics(ax: float, ay: float, vx: float, vy: float, bx: float, by: float) -> tuple[float, float, float]:
    va = np.array([ax - vx, ay - vy], dtype=np.float64)
    vb = np.array([bx - vx, by - vy], dtype=np.float64)
    len_a = float(np.hypot(va[0], va[1]))
    len_b = float(np.hypot(vb[0], vb[1]))

    if len_a <= 1e-12 or len_b <= 1e-12:
        return (0.0, len_a, len_b)

    cos_theta = float(np.dot(va, vb) / (len_a * len_b))
    cos_theta = float(np.clip(cos_theta, -1.0, 1.0))
    angle_deg = float(np.degrees(np.arccos(cos_theta)))
    return (angle_deg, len_a, len_b)


def _angle_overlay_spec(
    x1: float,
    y1: float,
    xm: float,
    ym: float,
    x2: float,
    y2: float,
    angle_deg: float,
    label_dx: float,
    label_dy: float,
    line_thickness: float,
    color: str,
) -> dict[str, float | str]:
    return {
        "kind": "angle_measure",
        "x1": x1,
        "y1": y1,
        "xm": xm,
        "ym": ym,
        "x2": x2,
        "y2": y2,
        "angle_deg": float(angle_deg),
        "label_dx": float(label_dx),
        "label_dy": float(label_dy),
        "line_thickness": float(line_thickness),
        "color": str(color),
    }


@register_node(display_name="Angle Measure")
class AngleMeasure:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("ANNOTATION_SOURCE", {"label": "Input"}),
                "color": ("STRING", {"default": "#ff0000", "color_picker": True}),
                "line_thickness": ("FLOAT", {
                    "default": 1.35,
                    "min": 0.35,
                    "max": 6.0,
                    "step": 0.05,
                    "label": "line thickness",
                    "hide_when_input_connected": "line_thickness_input",
                }),
                "x1": ("FLOAT", {"default": 0.22, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y1": ("FLOAT", {"default": 0.72, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "xm": ("FLOAT", {"default": 0.50, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "ym": ("FLOAT", {"default": 0.50, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "x2": ("FLOAT", {"default": 0.78, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "y2": ("FLOAT", {"default": 0.28, "min": 0.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "label_dx": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
                "label_dy": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01, "hidden": True}),
            },
            "optional": {
                "line_thickness_input": ("FLOAT", {"label": "line thickness"}),
            },
        }

    RETURN_TYPES = ("ANNOTATION_SOURCE", "MEASURE_TABLE")
    RETURN_NAMES = ("output", "measurements")
    FUNCTION = "process"

    DESCRIPTION = (
        "Measure the included angle between two draggable line segments over a DATA_FIELD or IMAGE. "
        "Drag either endpoint to change that arm, drag the middle joint to move the whole widget, "
        "drag the angle label to reposition it, choose the overlay color, and adjust line thickness "
        "with the widget or a FLOAT input."
    )

    def process(
        self,
        input,
        color: str,
        line_thickness: float,
        x1: float,
        y1: float,
        xm: float,
        ym: float,
        x2: float,
        y2: float,
        label_dx: float,
        label_dy: float,
        line_thickness_input: float | None = None,
    ) -> tuple:
        x1 = _clamp01(x1)
        y1 = _clamp01(y1)
        xm = _clamp01(xm)
        ym = _clamp01(ym)
        x2 = _clamp01(x2)
        y2 = _clamp01(y2)
        label_dx = float(np.clip(label_dx, -1.0, 1.0))
        label_dy = float(np.clip(label_dy, -1.0, 1.0))
        resolved_color = _normalize_markup_color(color, default="#ff0000")
        resolved_line_thickness = _sanitize_line_thickness(
            line_thickness_input if line_thickness_input is not None else line_thickness,
        )

        if isinstance(input, DataField):
            preview_base = render_datafield_preview(input, input.colormap)
            ax = float(input.xoff + x1 * input.xreal)
            ay = float(input.yoff + y1 * input.yreal)
            vx = float(input.xoff + xm * input.xreal)
            vy = float(input.yoff + ym * input.yreal)
            bx = float(input.xoff + x2 * input.xreal)
            by = float(input.yoff + y2 * input.yreal)
            length_unit = input.si_unit_xy
        else:
            preview_base = image_to_uint8(input)
            height, width = preview_base.shape[:2]
            ax = float(x1 * max(width - 1, 0))
            ay = float(y1 * max(height - 1, 0))
            vx = float(xm * max(width - 1, 0))
            vy = float(ym * max(height - 1, 0))
            bx = float(x2 * max(width - 1, 0))
            by = float(y2 * max(height - 1, 0))
            length_unit = "px"

        angle_deg, length_a, length_b = _angle_metrics(ax, ay, vx, vy, bx, by)
        angle_overlay = _angle_overlay_spec(
            x1=x1,
            y1=y1,
            xm=xm,
            ym=ym,
            x2=x2,
            y2=y2,
            angle_deg=angle_deg,
            label_dx=label_dx,
            label_dy=label_dy,
            line_thickness=resolved_line_thickness,
            color=resolved_color,
        )
        table = MeasureTable([
            {"quantity": "Angle", "value": angle_deg, "unit": "deg"},
            {"quantity": "Arm A length", "value": length_a, "unit": length_unit},
            {"quantity": "Arm B length", "value": length_b, "unit": length_unit},
            {"quantity": "Arm A x", "value": ax, "unit": length_unit},
            {"quantity": "Arm A y", "value": ay, "unit": length_unit},
            {"quantity": "Vertex x", "value": vx, "unit": length_unit},
            {"quantity": "Vertex y", "value": vy, "unit": length_unit},
            {"quantity": "Arm B x", "value": bx, "unit": length_unit},
            {"quantity": "Arm B y", "value": by, "unit": length_unit},
        ])

        if isinstance(input, DataField):
            output = input.replace(
                overlays=[
                    *input.overlays,
                    angle_overlay,
                ],
            )
        else:
            output = ImageData(
                _apply_angle_measure_overlay(preview_base, None, angle_overlay),
                metadata=image_metadata(input),
            )

        emit_overlay({
            "section_title": "Angle",
            "image": encode_preview(preview_base),
            **angle_overlay,
        })
        emit_table(table)

        return (output, table)
