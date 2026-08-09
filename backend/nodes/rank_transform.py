"""Rank transform — local contrast enhancement via a rank/presentation transform."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import grey_dilation, grey_erosion

from backend.data_types import DataField
from backend.node_registry import register_node


def _kernel_halfwidths(asize: int) -> np.ndarray:
    """Row half-widths of the inscribed ellipse of the (2*asize+1)^2 kernel.

    For each row offset k in [-asize, asize] the window extends
    floor(sqrt(0.25*size^2 - k^2)) pixels to each side.
    """
    size = 2 * asize + 1
    k = np.arange(-asize, asize + 1, dtype=np.float64)
    return np.floor(np.sqrt(0.25 * float(size * size) - k * k)).astype(np.int64)


def _elliptic_footprint(asize: int) -> np.ndarray:
    """Boolean support of the inscribed ellipse kernel."""
    halfwidths = _kernel_halfwidths(asize)
    size = 2 * asize + 1
    cols = np.arange(size) - asize
    rows = np.arange(size) - asize
    return np.abs(cols[np.newaxis, :]) <= halfwidths[rows][:, np.newaxis]


def _local_rank(data: np.ndarray, asize: int, halfwidths: np.ndarray,
                chunk_rows: int = 64) -> np.ndarray:
    """Fraction of elliptic-window pixels not exceeding the center pixel.

    Conservative rank filter whose window is the ellipse inscribed in the
    (2*asize+1)^2 square, truncated at the data edges, and tied values count
    with weight 1/2.  Computed in row chunks with per-row-offset segment
    gathering and sorting.
    """
    yres, xres = data.shape
    window = 2 * asize + 1
    k = np.arange(-asize, asize + 1)
    num = np.empty((yres, xres))
    den = np.empty((yres, xres))

    for row0 in range(0, yres, chunk_rows):
        row1 = min(row0 + chunk_rows, yres)
        rows = np.arange(row0, row1)
        nch = row1 - row0
        num_c = np.zeros((nch, xres))
        den_c = np.zeros((nch, xres))
        center = data[rows]

        for it, off in enumerate(k):
            w = int(halfwidths[it])
            r = rows + off
            valid = (r >= 0) & (r < yres)
            if not valid.any():
                continue
            row_vals = data[r[valid]]
            vv = center[valid]

            width = 2 * w + 1
            rowpad = np.pad(row_vals, ((0, 0), (w, w)), mode="edge")
            seg = np.lib.stride_tricks.sliding_window_view(rowpad, width, axis=1)
            seg = seg[:, :xres, :]                       # (nv, xres, width)
            # Columns of the segment falling outside the field are not part of
            # the C window: mask them out with +inf so they never compare <= v.
            j_idx = np.arange(xres)[:, None] + np.arange(-w, w + 1)[None, :]
            oob = (j_idx < 0) | (j_idx >= xres)
            seg = np.where(oob[np.newaxis, :, :], np.inf, seg)
            vv3 = vv[..., np.newaxis]
            # Count values strictly below and at most the center value; the
            # +inf masked-out entries never compare <= v.
            cl = (seg < vv3).sum(axis=-1)
            cr = (seg <= vv3).sum(axis=-1)
            num_c[valid] += 0.5 * (cl + cr)
            den_c[valid] += width - oob.sum(axis=-1)

        num[row0:row1] = num_c
        den[row0:row1] = den_c

    return num / den


def _normalize(data: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1]; a constant field becomes all zeros.

    Mirrors the standard min-max normalization.
    """
    dmin = float(data.min())
    dmax = float(data.max())
    if dmin == dmax:
        return np.zeros_like(data)
    return (data - dmin) / (dmax - dmin)


@register_node(display_name="Rank")
class RankTransform:
    CATEGORY = "Display"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "size": ("INT", {"default": 15, "min": 1, "max": 129}),
                "filter_type": (["rank", "normalization", "range"], {"default": "rank"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'rank'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Enhance local contrast with a rank transform. 'rank' replaces every "
        "pixel by the fraction of its elliptic kernel neighborhood (inscribed "
        "in a (2*size+1)^2 square) whose values do not exceed it, 'range' by the "
        "local value range (max - min) and 'normalization' by the local "
        "normalization (v - min)/(max - min). The result is min-max normalized "
        "to [0, 1] and unitless."
    )

    KEYWORDS = ("rank", "contrast", "presentation", "local", "normalize", "range")

    def process(self, field: DataField, size: int, filter_type: str) -> tuple:
        if filter_type not in ("rank", "normalization", "range"):
            raise ValueError(f"Unknown filter type: {filter_type!r}")
        if size < 1:
            raise ValueError("Kernel size must be at least 1")

        data = np.asarray(field.data, dtype=np.float64)
        halfwidths = _kernel_halfwidths(size)

        if filter_type == "rank":
            result = _local_rank(data, size, halfwidths)
        else:
            kernel = _elliptic_footprint(size)
            dmax = grey_dilation(data, footprint=kernel, mode="nearest")
            dmin = grey_erosion(data, footprint=kernel, mode="nearest")
            if filter_type == "range":
                result = dmax - dmin
            else:
                with np.errstate(divide="ignore", invalid="ignore"):
                    result = np.where(dmax > dmin, (data - dmin) / (dmax - dmin), 0.5)

        return (field.replace(data=_normalize(result), si_unit_z=""),)
