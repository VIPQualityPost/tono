from __future__ import annotations

import warnings

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


def _mark_scars_one_sign(
    data: np.ndarray,
    threshold_high: float,
    threshold_low: float,
    min_length: int,
    max_width: int,
    negative: bool,
) -> np.ndarray:
    yres, xres = data.shape
    marks = np.zeros_like(data, dtype=np.float64)

    min_length = max(int(min_length), 1)
    max_width = min(int(max_width), yres - 2)
    threshold_high = max(float(threshold_high), float(threshold_low))
    threshold_low = float(threshold_low)

    if min_length > xres or max_width < 1 or threshold_low <= 0.0:
        return marks

    vertical_rms = float(np.sqrt(np.sum((data[:-1] - data[1:]) ** 2) / max(xres * yres, 1)))
    if vertical_rms == 0.0:
        return marks

    for i in range(yres - (max_width + 1)):
        for j in range(xres):
            if negative:
                top = data[i, j]
                bottom = data[i + 1, j]
                width = 0
                for candidate in range(1, max_width + 1):
                    top = min(data[i, j], data[i + candidate + 1, j])
                    bottom = max(bottom, data[i + candidate, j])
                    if top - bottom >= threshold_low * vertical_rms:
                        width = candidate
                        break

                if width:
                    for candidate in range(width, 0, -1):
                        marks[i + candidate, j] = max(
                            marks[i + candidate, j],
                            (top - data[i + candidate, j]) / vertical_rms,
                        )
            else:
                bottom = data[i, j]
                top = data[i + 1, j]
                width = 0
                for candidate in range(1, max_width + 1):
                    bottom = max(data[i, j], data[i + candidate + 1, j])
                    top = min(top, data[i + candidate, j])
                    if top - bottom >= threshold_low * vertical_rms:
                        width = candidate
                        break

                if width:
                    for candidate in range(width, 0, -1):
                        marks[i + candidate, j] = max(
                            marks[i + candidate, j],
                            (data[i + candidate, j] - bottom) / vertical_rms,
                        )

    for i in range(yres):
        row = marks[i]
        for j in range(1, xres):
            if row[j] >= threshold_low and row[j - 1] >= threshold_high:
                row[j] = threshold_high
        for j in range(xres - 1, 0, -1):
            if row[j - 1] >= threshold_low and row[j] >= threshold_high:
                row[j - 1] = threshold_high

    for i in range(yres):
        row = marks[i]
        run_length = 0
        for j in range(xres):
            if row[j] >= threshold_high:
                row[j] = 1.0
                run_length += 1
                continue

            if 0 < run_length < min_length:
                row[j - run_length:j] = 0.0
            row[j] = 0.0
            run_length = 0

        if 0 < run_length < min_length:
            row[xres - run_length:xres] = 0.0

    return marks


def _mark_scars(
    data: np.ndarray,
    scar_type: str,
    threshold_high: float,
    threshold_low: float,
    min_length: int,
    max_width: int,
) -> np.ndarray:
    if scar_type == "positive":
        return _mark_scars_one_sign(data, threshold_high, threshold_low, min_length, max_width, negative=False)
    if scar_type == "negative":
        return _mark_scars_one_sign(data, threshold_high, threshold_low, min_length, max_width, negative=True)
    if scar_type == "both":
        positive = _mark_scars_one_sign(data, threshold_high, threshold_low, min_length, max_width, negative=False)
        negative = _mark_scars_one_sign(data, threshold_high, threshold_low, min_length, max_width, negative=True)
        return np.maximum(positive, negative)
    raise ValueError(f"Unknown scar type: {scar_type}")


def _laplace_inpaint(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    if not np.any(mask):
        return data.copy()

    if np.all(mask):
        return np.zeros_like(data, dtype=np.float64)

    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import MatrixRankWarning, spsolve
    from skimage.restoration import inpaint_biharmonic

    yres, xres = data.shape
    unknown_indices = -np.ones((yres, xres), dtype=np.int64)
    unknown_coords = np.argwhere(mask)
    unknown_indices[mask] = np.arange(unknown_coords.shape[0], dtype=np.int64)

    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []
    rhs = np.zeros(unknown_coords.shape[0], dtype=np.float64)

    for row_index, (y, x) in enumerate(unknown_coords):
        degree = 0
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if ny < 0 or ny >= yres or nx < 0 or nx >= xres:
                continue

            degree += 1
            if mask[ny, nx]:
                rows.append(row_index)
                cols.append(int(unknown_indices[ny, nx]))
                values.append(-1.0)
            else:
                rhs[row_index] += float(data[ny, nx])

        rows.append(row_index)
        cols.append(row_index)
        values.append(float(degree))

    matrix = csr_matrix((values, (rows, cols)), shape=(unknown_coords.shape[0], unknown_coords.shape[0]))
    restored = data.copy()

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=MatrixRankWarning)
            solved = spsolve(matrix, rhs)
    except (MatrixRankWarning, RuntimeError, ValueError):
        return np.asarray(inpaint_biharmonic(data, mask, channel_axis=None), dtype=np.float64)

    restored[mask] = np.asarray(solved, dtype=np.float64)
    return restored


@register_node(display_name="Scar Removal")
class ScarRemoval:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "scar_type": (["both", "positive", "negative"], {"default": "both"}),
                "threshold_high": ("FLOAT", {"default": 0.666, "min": 0.0, "max": 2.0, "step": 0.01}),
                "threshold_low": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 2.0, "step": 0.01}),
                "min_length": ("INT", {"default": 16, "min": 1, "max": 4096, "step": 1}),
                "max_width": ("INT", {"default": 4, "min": 1, "max": 32, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
        ('IMAGE', 'scar_mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect and remove horizontal scan scars using Gwyddion-derived scar marking thresholds, "
        "then interpolate over the detected mask with a Laplace-style inpaint."
    )

    def process(
        self,
        field: DataField,
        scar_type: str,
        threshold_high: float,
        threshold_low: float,
        min_length: int,
        max_width: int,
    ) -> tuple:
        threshold_high = float(max(threshold_high, threshold_low))
        threshold_low = float(min(threshold_high, threshold_low))

        marks = _mark_scars(
            np.asarray(field.data, dtype=np.float64),
            scar_type,
            threshold_high,
            threshold_low,
            int(min_length),
            int(max_width),
        )
        scar_mask = marks > 0.0
        corrected = _laplace_inpaint(np.asarray(field.data, dtype=np.float64), scar_mask)
        return (field.replace(data=corrected), scar_mask.astype(np.uint8) * 255)
