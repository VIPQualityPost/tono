"""Grain Selection Shapes — create selections visualizing inscribed discs or
circumscribed circles of grains (port of Gwyddion modules/process/grain_makesel.c
with the quantity algorithms from libprocess/grains-values.c)."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, label
from scipy.spatial import ConvexHull, QhullError

from backend.node_registry import register_node
from backend.nodes.helpers import mask_to_bool

# 12 shift directions every 7.5 degrees (grains-values.c shift_directions[]).
_SHIFT_DIRECTIONS = np.array([
    [1.0, 0.0],
    [0.9914448613738104, 0.1305261922200516],
    [0.9659258262890683, 0.2588190451025207],
    [0.9238795325112867, 0.3826834323650898],
    [0.8660254037844387, 0.5],
    [0.7933533402912352, 0.6087614290087207],
    [0.7071067811865476, 0.7071067811865475],
    [0.6087614290087207, 0.7933533402912352],
    [0.5, 0.8660254037844386],
    [0.3826834323650898, 0.9238795325112867],
    [0.2588190451025207, 0.9659258262890683],
    [0.1305261922200517, 0.9914448613738104],
], dtype=np.float64)


def _grain_circles(binary: np.ndarray, method: str, min_area: int) -> list[tuple[float, float, float]]:
    """Return (cx, cy, r) in pixel coordinates for each qualifying grain."""
    yres, xres = binary.shape
    labels, ngrains = label(binary)
    circles: list[tuple[float, float, float]] = []
    for gno in range(1, ngrains + 1):
        ys, xs = np.nonzero(labels == gno)
        if len(ys) < max(1, int(min_area)):
            continue
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        grain = labels[y0:y1, x0:x1] == gno
        if method == "inscribed_discs":
            # Distance from each pixel to the nearest non-grain pixel; the
            # per-grain estimate includes area outside the bounding box (like
            # the C's per-grain extraction and erosion).
            dist = distance_transform_edt(labels == gno)
            circles.append(_inscribed_disc(grain, y0, x0, dist[y0:y1, x0:x1]))
        else:
            circles.append(_circumscribed_circle(grain, y0, x0))
    return circles


def _inscribed_disc(grain: np.ndarray, y0: int, x0: int,
                    dist: np.ndarray) -> tuple[float, float, float]:
    """Largest disc inside the grain: Euclidean distance transform maximum, ties
    resolved towards the grain centre of mass. Radius from pixel-centre distances
    converted to geometric half-widths (EDT - 0.5), matching the continuous
    inscribed disc semantics of GWY_GRAIN_VALUE_INSCRIBED_DISC_R."""
    dmax = float(dist[grain].max())
    centre_y, centre_x = (float(v) for v in np.mean(np.argwhere(grain), axis=0))
    candidates = np.argwhere(np.isclose(dist, dmax))
    closest = candidates[np.argmin(np.sum((candidates - np.array([centre_y, centre_x])) ** 2, axis=1))]
    centre_y = float(closest[0]) + y0
    centre_x = float(closest[1]) + x0
    radius = max(0.5, dmax - 0.5)
    return centre_x, centre_y, radius


def _circumscribed_circle(grain: np.ndarray, y0: int, x0: int) -> tuple[float, float, float]:
    """Smallest enclosing circle of the grain's pixel corners: convex hull,
    polygon-centroid start, then the greedy shift refinement of
    improve_circumscribed_circle() from grains-values.c."""
    ys, xs = np.nonzero(grain)
    corners = np.unique(np.column_stack([
        np.concatenate([xs, xs, xs + 1, xs + 1]),
        np.concatenate([ys, ys + 1, ys, ys + 1]),
    ]), axis=0).astype(np.float64)
    if len(corners) < 3:
        return float(xs[0]) + x0, float(ys[0]) + y0, np.sqrt(0.5)
    try:
        hull = ConvexHull(corners)
    except QhullError:
        return float(np.mean(xs)) + x0, float(np.mean(ys)) + y0, 0.5
    vertices = corners[hull.vertices]

    # Polygon centroid (grain_convex_hull_centre()).
    a = vertices[0]
    s = 0.0
    xc = yc = 0.0
    for k in range(1, len(vertices) - 1):
        b, c = vertices[k], vertices[k + 1]
        s1 = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        xc += s1 * (a[0] + b[0] + c[0])
        yc += s1 * (a[1] + b[1] + c[1])
        s += s1
    if s != 0.0:
        cx, cy = xc / (3.0 * s), yc / (3.0 * s)
    else:
        cx, cy = float(np.mean(vertices[:, 0])), float(np.mean(vertices[:, 1]))

    def circum_r2(x: float, y: float) -> float:
        delta = vertices - np.array([x, y])
        return float(np.max(delta[:, 0] ** 2 + delta[:, 1] ** 2))

    r2 = circum_r2(cx, cy)
    eps = 1.0
    improvement = 0.0
    for _ in range(200):
        best = (cx, cy, r2)
        for dxs, dys in _SHIFT_DIRECTIONS:
            sx, sy = eps * dxs, eps * dys
            for dxn, dyn in ((sx, sy), (-sy, sx), (-sx, -sy), (sy, -sx)):
                cand_r2 = circum_r2(cx + dxn, cy + dyn)
                if cand_r2 < best[2]:
                    best = (cx + dxn, cy + dyn, cand_r2)
        if best[2] < r2:
            improvement = best[2] - r2
            cx, cy, r2 = best
        else:
            eps *= 0.5
            improvement = 0.0
        if eps <= 1e-3 and improvement <= 1e-3:
            break

    return cx + x0, cy + y0, float(np.sqrt(r2))


def _rasterize_circles(yres: int, xres: int,
                       circles: list[tuple[float, float, float]]) -> np.ndarray:
    yy, xx = np.mgrid[0:yres, 0:xres]
    out = np.zeros((yres, xres), dtype=np.uint8)
    for cx, cy, r in circles:
        if r <= 0.0:
            continue
        inside = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r
        out[inside] = 255
    return out


@register_node(display_name="Grain Selection Shapes")
class GrainSelectionShapes:
    CATEGORY = "Grains"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "method": (["inscribed_discs", "circumscribed_circles"], {"default": "inscribed_discs"}),
                "min_area": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'selection'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Create a selection image visualizing the largest disc that fits inside "
        "each grain (inscribed discs) or the smallest circle enclosing each grain "
        "(circumscribed circles), mirroring Gwyddion's Select Inscribed Discs and "
        "Select Circumscribed Circles. Grains are found as 4-connected components "
        "of the input mask; grains smaller than the minimum area are skipped."
    )

    KEYWORDS = ("grain", "inscribed", "circumscribed", "disc", "circle", "selection")

    def process(self, mask: np.ndarray, method: str, min_area: int) -> tuple:
        if method not in ("inscribed_discs", "circumscribed_circles"):
            raise ValueError(f"Unknown method: {method!r}")
        mask_array = np.asarray(mask)
        binary = mask_array if mask_array.dtype == bool else mask_to_bool(mask_array)
        yres, xres = binary.shape
        circles = _grain_circles(binary, method, int(min_area))
        selection = _rasterize_circles(yres, xres, circles)
        return (selection,)
