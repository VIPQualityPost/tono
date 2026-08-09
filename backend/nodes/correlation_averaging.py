from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import correlate2d

from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.node_registry import register_node

# Gaussian smoothing sigma of the correlation score: FWHM of 2 px, i.e.
# sigma = 2.0 / (2.0 * sqrt(2.0 * ln 2)) ~= 0.8493
_SMOOTH_SIGMA = 2.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))


def _gather_mean(a: np.ndarray, kx: int, ky: int) -> np.ndarray:
    """Clipped local-window arithmetic mean.

    The window centred on each sample covers [j-(kx-1)/2, j+kx/2] x
    [i-(ky-1)/2, i+ky/2]; where it extends out of the field only the in-bounds
    samples are averaged.
    """
    yres, xres = a.shape
    hs2m, hs2p = (kx - 1) // 2, kx // 2
    vs2m, vs2p = (ky - 1) // 2, ky // 2
    # Data row i sits at padded row vs2m+1+i (one extra leading zero row/column
    # makes the cumsum exclusive: cs[k, l] = sum pad[0:k, 0:l]).
    pad = np.zeros((yres + vs2m + vs2p + 2, xres + hs2m + hs2p + 2))
    pad[vs2m + 1:vs2m + 1 + yres, hs2m + 1:hs2m + 1 + xres] = a
    cs = np.cumsum(np.cumsum(pad, axis=0), axis=1)

    # Window rows [i-vs2m, i+vs2p] and cols [j-hs2m, j+hs2p] in data coordinates
    # correspond to padded block rows [i+1, i+1+vs2m+vs2p] (same for columns).
    i = np.arange(yres)[:, np.newaxis]
    j = np.arange(xres)[np.newaxis, :]
    bottom = i + vs2m + vs2p + 1
    right = j + hs2m + hs2p + 1
    total = cs[bottom, right] - cs[i, right] - cs[bottom, j] + cs[i, j]

    count = (np.minimum(i + vs2p, yres - 1) - np.maximum(i - vs2m, 0) + 1) * (
        np.minimum(j + hs2p, xres - 1) - np.maximum(j - hs2m, 0) + 1
    )
    return total / count


def _normalized_correlation_score(data: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Normalised correlation score field.

    The score at pixel (j, i) is the mean of (d - davg)*(k - kavg) over the
    kernel window centred on (j, i), divided by the product of the local RMS of
    the data and the RMS of the kernel.  Positions where the kernel does not fit
    completely keep the value -1.  The raw window sum matches
    scipy.signal.correlate2d(mode="same") for both even and odd kernel sizes.
    """
    yres, xres = data.shape
    ky, kx = kernel.shape
    xoff, yoff = (kx - 1) // 2, (ky - 1) // 2

    kavg = float(kernel.mean())
    krms = float(np.sqrt(np.mean((kernel - kavg) ** 2)))

    davg = _gather_mean(data, kx, ky)
    dvar = np.clip(_gather_mean(data * data, kx, ky) - davg * davg, 0.0, None)
    drms = np.sqrt(dvar)

    # Sum over the window of d*k with kernel top-left at (j-xoff, i-yoff).
    win_dk = correlate2d(data, kernel, mode="same")
    score = (win_dk - davg * kavg * kx * ky) / (kx * ky)
    with np.errstate(divide="ignore", invalid="ignore"):
        score = score / (drms * krms)
    score = np.where((krms == 0.0) | (drms == 0.0), 0.0, score)

    valid = np.zeros((yres, xres), dtype=bool)
    valid[yoff:yres - ky + yoff + 1, xoff:xres - kx + xoff + 1] = True
    score = np.where(valid, score, -1.0)
    return score


def _find_local_maxima(score: np.ndarray, threshold_fraction: float = 0.75) -> list[tuple[int, int, float]]:
    """Local maxima of the smoothed score (4-neighbourhood, >= comparison).

    Pixel (i, j) is kept when no strict 4-neighbour is larger and the value
    exceeds threshold_fraction * max.  Returns (row, col, value) triples in scan
    order.
    """
    yres, xres = score.shape
    pad = np.pad(score, 1, mode="constant", constant_values=-np.inf)
    is_max = (
        (score >= pad[:-2, 1:-1])
        & (score >= pad[2:, 1:-1])
        & (score >= pad[1:-1, :-2])
        & (score >= pad[1:-1, 2:])
    )
    is_max[0, :] = is_max[-1, :] = False
    is_max[:, 0] = is_max[:, -1] = False
    mask = is_max & (score > threshold_fraction * float(score.max()))
    rows, cols = np.nonzero(mask)
    return [(int(r), int(c), float(score[r, c])) for r, c in zip(rows, cols)]


@register_node(display_name="Correlation Averaging")
class CorrelationAveraging:
    CATEGORY = "Level & Correct"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "x": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 1e-9}),
                "y": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 1e-9}),
                "width": ("FLOAT", {"default": 1e-7, "min": 1e-12, "max": 1.0, "step": 1e-9}),
                "height": ("FLOAT", {"default": 1e-7, "min": 1e-12, "max": 1.0, "step": 1e-9}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'averaged'),
        ('RECORD_TABLE', 'alignment'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Average repeats of a periodic structure to remove noise. The rectangle "
        "(x, y, width, height in physical "
        "units) selects one representative repeat used as the template. The image "
        "is normalised-cross-correlated with the template, correlation maxima above "
        "75% of the peak are located, and the template-sized patches at those "
        "positions are averaged and copied back. The alignment table reports each "
        "detected repeat's offset from the template in pixels and its correlation."
    )

    KEYWORDS = ("averaging", "correlation", "periodic", "repeat", "alignment", "template", "denoise")

    def process(
        self,
        field: DataField,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        px = xres / field.xreal if field.xreal else 0.0
        py = yres / field.yreal if field.yreal else 0.0
        if px <= 0.0 or py <= 0.0:
            raise ValueError("Field has invalid physical extents (xreal/xres must be positive)")

        # Pixel conversion: truncation toward zero, offsets ignored.
        x0 = int(np.trunc(float(x) * px))
        y0 = int(np.trunc(float(y) * py))
        x1 = int(np.trunc((float(x) + float(width)) * px))
        y1 = int(np.trunc((float(y) + float(height)) * py))
        kw, kh = x1 - x0, y1 - y0
        if kw < 1 or kh < 1:
            raise ValueError(
                f"Template rectangle collapses to {kw}x{kh} px; increase width/height"
            )
        if x0 < 0 or y0 < 0 or x1 > xres or y1 > yres:
            raise ValueError(
                f"Template rectangle [{x0}:{x1}, {y0}:{y1}] px lies outside the "
                f"{xres}x{yres} px field"
            )
        if kw >= xres or kh >= yres:
            raise ValueError(f"Template ({kw}x{kh} px) must be smaller than the field")

        kernel = data[y0:y1, x0:x1].copy()

        # 1. Normalised cross-correlation of the field with the template.
        score = _normalized_correlation_score(data, kernel)
        # 2. Smooth the score with a Gaussian of FWHM 2 px.
        score = gaussian_filter(score, sigma=_SMOOTH_SIGMA)
        # 3. Find local maxima.
        maxima = _find_local_maxima(score)

        # 4. Weighted average of the template-sized patches around each maximum.
        res_kernel = np.zeros_like(kernel)
        divider = 0.0
        patches: list[tuple[int, int, float]] = []
        for row, col, zvalue in maxima:
            # gint xtop = maximum.col - width/2 with integer truncation.
            xtop = col - kw // 2
            ytop = row - kh // 2
            if xtop < 0 or ytop < 0 or xtop + kw > xres or ytop + kh > yres:
                # Defensive: skip patches that would extend out of the field.
                continue
            patches.append((xtop, ytop, zvalue))
            res_kernel += zvalue * data[ytop:ytop + kh, xtop:xtop + kw]
            divider += zvalue
        if divider <= 0.0:
            divider = 1.0
        res_kernel /= divider

        # 5. Copy the averaged patch back at every maximum position.
        result = data.copy()
        for xtop, ytop, _zvalue in patches:
            result[ytop:ytop + kh, xtop:xtop + kw] = res_kernel

        # Alignment table: per-detected-repeat shifts in px (C's score coordinates
        # are kernel centres, so the shift is relative to the template centre).
        tc_col = x0 + (kw - 1) / 2.0
        tc_row = y0 + (kh - 1) / 2.0
        rows: list[dict] = []
        for n, (row, col, zvalue) in enumerate(maxima, 1):
            rows.append({
                "quantity": f"Repeat {n} X offset",
                "value": float(col - tc_col),
                "unit": "px",
            })
            rows.append({
                "quantity": f"Repeat {n} Y offset",
                "value": float(row - tc_row),
                "unit": "px",
            })
            rows.append({
                "quantity": f"Repeat {n} correlation",
                "value": float(zvalue),
                "unit": "",
            })
        alignment = RecordTable(rows)
        emit_table(alignment)

        return (field.replace(data=result), alignment)
