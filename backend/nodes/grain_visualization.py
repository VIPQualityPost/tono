"""Grain visualization — visualize grains as geometric shapes."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label, find_objects, distance_transform_edt

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask


def _grain_centroid(grain_mask: np.ndarray, slc: tuple[slice, slice]) -> tuple[float, float]:
    """Return (cy, cx) centroid of a grain within its bounding slice."""
    ys, xs = np.where(grain_mask[slc])
    cy = float(ys.mean()) + slc[0].start
    cx = float(xs.mean()) + slc[1].start
    return cy, cx


def _grain_inscribed_radius(grain_mask: np.ndarray, slc: tuple[slice, slice]) -> float:
    """Return the inscribed disc radius for a grain region."""
    region = grain_mask[slc]
    if not np.any(region):
        return 0.0
    dt = distance_transform_edt(region)
    return float(dt.max())


def _grain_inertia(grain_mask: np.ndarray, slc: tuple[slice, slice]) -> tuple[float, float, float]:
    """Return (semi_major, semi_minor, angle_rad) from the inertia tensor."""
    ys, xs = np.where(grain_mask[slc])
    cy_local = ys.mean()
    cx_local = xs.mean()
    dy = ys - cy_local
    dx = xs - cx_local
    n = len(ys)
    if n < 2:
        return 1.0, 1.0, 0.0

    Ixx = np.sum(dy * dy) / n
    Iyy = np.sum(dx * dx) / n
    Ixy = -np.sum(dx * dy) / n

    # Eigenvalues of the 2x2 inertia tensor
    mean_I = (Ixx + Iyy) / 2.0
    diff_I = (Ixx - Iyy) / 2.0
    discriminant = max(0.0, diff_I ** 2 + Ixy ** 2)
    sqrt_disc = np.sqrt(discriminant)

    lambda1 = mean_I + sqrt_disc
    lambda2 = mean_I - sqrt_disc

    # Semi-axes proportional to sqrt of eigenvalues, scaled by 2 for visual size
    semi_major = 2.0 * np.sqrt(max(lambda1, 0.0))
    semi_minor = 2.0 * np.sqrt(max(lambda2, 0.0))

    # Angle of the major axis
    angle = 0.5 * np.arctan2(2.0 * Ixy, Iyy - Ixx)

    return float(semi_major), float(semi_minor), float(angle)


def _draw_circle_filled(canvas: np.ndarray, cy: float, cx: float, r: float) -> None:
    h, w = canvas.shape
    y_lo = max(0, int(cy - r - 1))
    y_hi = min(h, int(cy + r + 2))
    x_lo = max(0, int(cx - r - 1))
    x_hi = min(w, int(cx + r + 2))
    yy, xx = np.ogrid[y_lo:y_hi, x_lo:x_hi]
    dist_sq = (yy - cy) ** 2 + (xx - cx) ** 2
    canvas[y_lo:y_hi, x_lo:x_hi] |= (dist_sq <= r * r)


def _draw_circle_outline(canvas: np.ndarray, cy: float, cx: float, r: float, thickness: float = 1.5) -> None:
    h, w = canvas.shape
    y_lo = max(0, int(cy - r - thickness - 1))
    y_hi = min(h, int(cy + r + thickness + 2))
    x_lo = max(0, int(cx - r - thickness - 1))
    x_hi = min(w, int(cx + r + thickness + 2))
    yy, xx = np.ogrid[y_lo:y_hi, x_lo:x_hi]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    canvas[y_lo:y_hi, x_lo:x_hi] |= (np.abs(dist - r) < thickness)


def _draw_rect_filled(canvas: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> None:
    h, w = canvas.shape
    y0c, y1c = max(0, y0), min(h, y1)
    x0c, x1c = max(0, x0), min(w, x1)
    canvas[y0c:y1c, x0c:x1c] = True


def _draw_rect_outline(canvas: np.ndarray, y0: int, y1: int, x0: int, x1: int, thickness: int = 1) -> None:
    h, w = canvas.shape
    y0c, y1c = max(0, y0), min(h, y1)
    x0c, x1c = max(0, x0), min(w, x1)
    # Top edge
    canvas[y0c:min(h, y0c + thickness), x0c:x1c] = True
    # Bottom edge
    canvas[max(0, y1c - thickness):y1c, x0c:x1c] = True
    # Left edge
    canvas[y0c:y1c, x0c:min(w, x0c + thickness)] = True
    # Right edge
    canvas[y0c:y1c, max(0, x1c - thickness):x1c] = True


def _draw_cross(canvas: np.ndarray, cy: float, cx: float, arm: int = 3) -> None:
    h, w = canvas.shape
    iy, ix = int(round(cy)), int(round(cx))
    for d in range(-arm, arm + 1):
        if 0 <= iy + d < h and 0 <= ix < w:
            canvas[iy + d, ix] = True
        if 0 <= iy < h and 0 <= ix + d < w:
            canvas[iy, ix + d] = True


def _draw_ellipse_filled(canvas: np.ndarray, cy: float, cx: float,
                         semi_major: float, semi_minor: float, angle: float) -> None:
    h, w = canvas.shape
    r_max = max(semi_major, semi_minor, 1.0)
    y_lo = max(0, int(cy - r_max - 1))
    y_hi = min(h, int(cy + r_max + 2))
    x_lo = max(0, int(cx - r_max - 1))
    x_hi = min(w, int(cx + r_max + 2))
    yy, xx = np.ogrid[y_lo:y_hi, x_lo:x_hi]
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    dy = yy - cy
    dx = xx - cx
    # Rotate into ellipse-aligned coordinates
    u = cos_a * dx + sin_a * dy
    v = -sin_a * dx + cos_a * dy
    a = max(semi_major, 0.5)
    b = max(semi_minor, 0.5)
    canvas[y_lo:y_hi, x_lo:x_hi] |= ((u / a) ** 2 + (v / b) ** 2 <= 1.0)


def _draw_ellipse_outline(canvas: np.ndarray, cy: float, cx: float,
                          semi_major: float, semi_minor: float, angle: float,
                          thickness: float = 1.5) -> None:
    h, w = canvas.shape
    r_max = max(semi_major, semi_minor, 1.0)
    y_lo = max(0, int(cy - r_max - thickness - 1))
    y_hi = min(h, int(cy + r_max + thickness + 2))
    x_lo = max(0, int(cx - r_max - thickness - 1))
    x_hi = min(w, int(cx + r_max + thickness + 2))
    yy, xx = np.ogrid[y_lo:y_hi, x_lo:x_hi]
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    dy = yy - cy
    dx = xx - cx
    u = cos_a * dx + sin_a * dy
    v = -sin_a * dx + cos_a * dy
    a = max(semi_major, 0.5)
    b = max(semi_minor, 0.5)
    ellipse_val = (u / a) ** 2 + (v / b) ** 2
    canvas[y_lo:y_hi, x_lo:x_hi] |= (np.abs(np.sqrt(ellipse_val) - 1.0) < thickness / max(a, b))


@register_node(display_name="Grain Visualization")
class GrainVisualization:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "style": (["inscribed_disc", "bounding_box", "centroid", "ellipse"], {"default": "inscribed_disc"}),
                "fill": ("BOOLEAN", {"default": False}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'result'),
        ('DATA_FIELD', 'labeled'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Visualize labeled grains as geometric shapes — inscribed discs, bounding boxes, "
        "centroid markers, or fitted ellipses. Produces a mask image with the chosen shapes "
        "and a labeled field where each grain has a unique integer value. "
        "Equivalent to Gwyddion's grain selection visualization (grain_makesel)."
    )

    def process(self, field: DataField, mask: np.ndarray, style: str, fill: bool) -> tuple:
        mask_bool = mask_to_bool(mask)
        labels, n_grains = label(mask_bool.astype(np.int32))
        slices = find_objects(labels)

        h, w = mask_bool.shape[:2]
        canvas = np.zeros((h, w), dtype=bool)

        for gid in range(1, n_grains + 1):
            slc = slices[gid - 1]
            if slc is None:
                continue

            grain_mask = labels == gid
            cy, cx = _grain_centroid(grain_mask, slc)

            if style == "inscribed_disc":
                r = _grain_inscribed_radius(grain_mask, slc)
                if r < 0.5:
                    r = 0.5
                if fill:
                    _draw_circle_filled(canvas, cy, cx, r)
                else:
                    _draw_circle_outline(canvas, cy, cx, r)

            elif style == "bounding_box":
                y0, y1 = slc[0].start, slc[0].stop
                x0, x1 = slc[1].start, slc[1].stop
                if fill:
                    _draw_rect_filled(canvas, y0, y1, x0, x1)
                else:
                    _draw_rect_outline(canvas, y0, y1, x0, x1)

            elif style == "centroid":
                arm = max(3, int(round(min(h, w) * 0.01)))
                _draw_cross(canvas, cy, cx, arm)

            elif style == "ellipse":
                semi_major, semi_minor, angle = _grain_inertia(grain_mask, slc)
                if semi_major < 0.5:
                    semi_major = 0.5
                if semi_minor < 0.5:
                    semi_minor = 0.5
                if fill:
                    _draw_ellipse_filled(canvas, cy, cx, semi_major, semi_minor, angle)
                else:
                    _draw_ellipse_outline(canvas, cy, cx, semi_major, semi_minor, angle)

            else:
                raise ValueError(f"Unknown visualization style: {style!r}")

        result = bool_to_mask(canvas)
        labeled_field = field.replace(data=labels.astype(np.float64))

        return (result, labeled_field)
