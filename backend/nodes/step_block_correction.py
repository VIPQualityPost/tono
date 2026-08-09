"""Step Block Correction.

Corrects vertical steps in scan lines block-by-block, without any line
correction.  Discontinuities between consecutive scan lines that exceed a
threshold multiple of the RMS vertical difference are located, blocks are
built from the resulting marks, and each block's rows are shifted by the
trimmed mean of the step across the block segments.
"""

from __future__ import annotations

import numpy as np

from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.node_registry import register_node


def _trimmed_mean(values: np.ndarray, nlowest: int, nhighest: int) -> float:
    """Trimmed mean discarding *nlowest* lowest and *nhighest* highest values."""
    values = np.asarray(values, dtype=np.float64)
    n = values.size
    if n == 0:
        return 0.0
    nlowest = max(0, min(int(nlowest), n - 1))
    nhighest = max(0, min(int(nhighest), n - 1 - nlowest))
    if nlowest + nhighest >= n:
        return float(values.mean())
    sorted_values = np.sort(values, kind="mergesort")
    return float(sorted_values[nlowest:n - nhighest].mean())


def _vertical_rms(data: np.ndarray, xreal: float, yreal: float) -> float:
    """Typical vertical jump between adjacent rows.

    Computes the mean over rows of the RMS row slope (in vertical orientation)
    and multiplies it by the pixel height dy.
    """
    yres, xres = data.shape
    if xres < 2 or xreal <= 0.0:
        return 0.0
    diffs = np.diff(data, axis=1)
    per_row_rms_slope = np.sqrt(np.mean(diffs * diffs, axis=1)) * (xres / xreal)
    dy = yreal / yres if yres else 1.0
    return float(per_row_rms_slope.mean() * dy)


def _mark_discontinuities(
    data: np.ndarray,
    threshold: float,
    left_to_right: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Locate large vertical jumps and the best block split per scan row.

    Returns (pos, score) arrays indexed by scan row: pos is the column where
    the scan line is split, score the number of covered discontinuity marks.
    """
    yres, xres = data.shape
    imask = np.zeros((yres, xres), dtype=bool)
    if yres > 1:
        imask[1:] = np.abs(np.diff(data, axis=0)) > threshold
    totalsteps = imask.sum(axis=1)

    pos = np.full(yres, xres // 2, dtype=int)
    score = np.zeros(yres, dtype=np.float64)

    for i in range(1, yres):
        prev = np.cumsum(imask[i - 1].astype(np.int64))
        row = np.cumsum(imask[i].astype(np.int64))
        prev = np.concatenate(([0], prev))
        row = np.concatenate(([0], row))
        ntotal = int(totalsteps[i - 1] if left_to_right else totalsteps[i])

        if left_to_right:
            total = row + (ntotal - prev)
        else:
            total = prev + (ntotal - row)

        best = int(total.max())
        if best > 0:
            pos[i] = int(np.argmax(total))
            score[i] = best
    return pos, score


def _construct_blocks(
    data: np.ndarray,
    pos: np.ndarray,
    score: np.ndarray,
    left_to_right: bool,
) -> list[list]:
    """Select block starts from the scan-row splits.

    Returns (block_row, fromleft, score) triples; block_row is the raw scan
    index used to estimate the step (decremented afterwards).
    """
    yres, xres = data.shape
    minlength = int(3 * xres / 4)
    blocks: list[list] = []

    for i in range(1, yres):
        if score[i] < minlength:
            continue
        if left_to_right and pos[i] == xres:
            if i == yres - 1:
                continue
            blocks.append([i + 1, 0, float(score[i])])
        elif not left_to_right and pos[i] == 0:
            if i == yres - 1:
                continue
            blocks.append([i + 1, xres, float(score[i])])
        else:
            blocks.append([i, int(pos[i]), float(score[i])])

    # Do not allow blocks on consecutive lines; keep the better-scoring one.
    k = len(blocks) - 1
    while k >= 1:
        bs0, bs1 = blocks[k - 1], blocks[k]
        if bs1[0] - bs0[0] <= 1:
            del blocks[k - 1 if bs1[2] > bs0[2] else k]
        k -= 1
    return blocks


def _estimate_block_shifts(
    data: np.ndarray,
    blocks: list[list],
    left_to_right: bool,
) -> list[tuple]:
    """Estimate each block's step from the row differences across its segments.

    Port of the block processing loop in construct_blocks(): for every block
    the step is the trimmed mean (xres/4 on each side) of the differences
    between the rows right below and right above the discontinuity, taken on
    the two complementary horizontal segments.
    """
    xres = data.shape[1]
    final: list[tuple] = []
    for bi, fromleft, _score in blocks:
        shifts = np.empty(xres, dtype=np.float64)
        if left_to_right:
            shifts[0:fromleft] = data[bi][0:fromleft] - data[bi - 1][0:fromleft]
            shifts[fromleft:xres] = data[bi - 1][fromleft:xres] - data[bi - 2][fromleft:xres]
        else:
            shifts[fromleft:xres] = data[bi][fromleft:xres] - data[bi - 1][fromleft:xres]
            shifts[0:fromleft] = data[bi - 1][0:fromleft] - data[bi - 2][0:fromleft]
        step = _trimmed_mean(shifts, xres // 4, xres // 4)
        final.append((bi - 1, fromleft, step))
    return final


def _apply_correction(data: np.ndarray, blocks: list[tuple], left_to_right: bool) -> np.ndarray:
    """Shift rows below each block by its (negated) step.

    At the block start row the left part keeps the accumulated shift while
    the right part (from *fromleft*) receives the new one; all rows below
    are shifted fully.
    """
    result = data.copy()
    yres, xres = result.shape
    if not blocks:
        return result

    shift = 0.0
    b_idx = 0
    nblocks = len(blocks)
    for i in range(blocks[0][0], yres):
        row = result[i]
        if b_idx < nblocks and i == blocks[b_idx][0]:
            _bi, fromleft, bshift = blocks[b_idx]
            if left_to_right:
                row[:fromleft] += shift
                shift -= bshift
                row[fromleft:] += shift
            else:
                row[fromleft:] += shift
                shift -= bshift
                row[:fromleft] += shift
            b_idx += 1
        else:
            row += shift
    return result


@register_node(display_name="Step Block Correction")
class StepBlockCorrection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "threshold": ("FLOAT", {
                    "default": 2.0,
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                }),
                "scan_direction": (["left_to_right", "right_to_left"], {
                    "default": "left_to_right",
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
        ('RECORD_TABLE', 'stats'),
    )
    FUNCTION = "process"
    CATEGORY = "Level & Correct"

    DESCRIPTION = (
        "Correct vertical steps in scan lines block-by-block. "
        "Discontinuities between consecutive lines larger than the threshold "
        "times the RMS vertical difference are located; each detected block is "
        "shifted by the trimmed mean of its step. The stats table reports the "
        "estimated step, row and split column of every block."
    )

    KEYWORDS = ("step", "block", "terrace", "line", "discontinuity", "correct")

    def process(
        self,
        field: DataField,
        threshold: float,
        scan_direction: str,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        if data.ndim != 2:
            raise ValueError("Step Block Correction requires a 2-D data field.")

        if scan_direction == "left_to_right":
            left_to_right = True
        elif scan_direction == "right_to_left":
            left_to_right = False
        else:
            raise ValueError(f"Unknown scan direction: {scan_direction}")

        rms = _vertical_rms(data, float(field.xreal), float(field.yreal))
        threshold_abs = float(threshold) * rms

        pos, score = _mark_discontinuities(data, threshold_abs, left_to_right)
        blocks = _construct_blocks(data, pos, score, left_to_right)

        rows = [{"quantity": "Detected blocks", "value": len(blocks), "unit": ""}]
        corrected_data = data.copy()

        if blocks:
            final = _estimate_block_shifts(data, blocks, left_to_right)
            corrected_data = _apply_correction(data, final, left_to_right)
            for k, (_row, fromleft, step) in enumerate(final):
                rows.append({"quantity": f"Block {k + 1} step", "value": float(step), "unit": field.si_unit_z})
                rows.append({"quantity": f"Block {k + 1} row", "value": float(_row), "unit": "px"})
                rows.append({"quantity": f"Block {k + 1} split column", "value": float(fromleft), "unit": "px"})

        stats = RecordTable(rows)
        emit_table(stats)
        return (field.replace(data=corrected_data), stats)
