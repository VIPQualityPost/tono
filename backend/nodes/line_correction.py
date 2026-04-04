from __future__ import annotations

import numpy as np

from backend.data_types import DataField, LineData
from backend.node_registry import register_node
from backend.nodes.helpers import normalize_mask, apply_masking, masked_values


def _trimmed_mean_or_median(values: np.ndarray, trim_fraction: float) -> float:
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return 0.0

    sorted_values = np.sort(values, kind="mergesort")
    count = sorted_values.size
    nlowest = int(np.rint(trim_fraction * count))
    nhighest = int(np.rint(trim_fraction * count))

    if nlowest + nhighest + 1 >= count:
        return float(np.median(sorted_values))

    trimmed = sorted_values[nlowest:count - nhighest]
    return float(trimmed.mean()) if trimmed.size else float(np.median(sorted_values))


def _global_masked_median(data: np.ndarray, mask: np.ndarray | None, masking: str) -> float:
    selected = masked_values(data, mask, masking)
    if selected.size == 0:
        selected = np.asarray(data, dtype=np.float64).ravel()
    return float(np.median(selected))


def _find_row_shifts_trimmed_mean(
    data: np.ndarray,
    mask: np.ndarray | None,
    masking: str,
    trim_fraction: float,
    mincount: int = 0,
) -> np.ndarray:
    yres, xres = data.shape
    if yres == 0:
        return np.zeros(0, dtype=np.float64)

    if mincount <= 0:
        mincount = int(np.rint(np.log(max(xres, 1)) + 1.0))

    total_median = _global_masked_median(data, mask, masking)
    shifts = np.empty(yres, dtype=np.float64)

    for i in range(yres):
        row = data[i]
        row_mask = None if mask is None else mask[i]

        if row_mask is None or masking == "ignore":
            shifts[i] = _trimmed_mean_or_median(row, trim_fraction)
            continue

        values = masked_values(row, row_mask, masking)
        if values.size >= mincount:
            shifts[i] = _trimmed_mean_or_median(values, trim_fraction)
        else:
            shifts[i] = total_median

    shifts -= shifts.mean()
    return shifts


def _slope_level_row_shifts(shifts: np.ndarray) -> np.ndarray:
    shifts = np.asarray(shifts, dtype=np.float64).copy()
    if shifts.size <= 1:
        shifts -= shifts.mean() if shifts.size else 0.0
        return shifts

    x = np.arange(shifts.size, dtype=np.float64)
    A = np.column_stack((np.ones_like(x), x))
    coeffs, _, _, _ = np.linalg.lstsq(A, shifts, rcond=None)
    intercept, slope = coeffs
    shifts -= intercept + slope * x
    return shifts


def _find_row_shifts_trimmed_diff(
    data: np.ndarray,
    mask: np.ndarray | None,
    masking: str,
    trim_fraction: float,
    mincount: int = 0,
) -> np.ndarray:
    yres, xres = data.shape
    shifts = np.zeros(yres, dtype=np.float64)
    if yres <= 1:
        return shifts

    if mincount <= 0:
        mincount = int(np.rint(np.log(max(xres, 1)) + 1.0))

    for i in range(yres - 1):
        upper = data[i]
        lower = data[i + 1]

        if mask is None or masking == "ignore":
            diffs = lower - upper
        else:
            upper_mask = mask[i]
            lower_mask = mask[i + 1]
            valid = upper_mask & lower_mask if masking == "include" else (~upper_mask & ~lower_mask)
            diffs = (lower - upper)[valid]

        if diffs.size >= mincount:
            shifts[i + 1] = _trimmed_mean_or_median(diffs, trim_fraction)
        else:
            shifts[i + 1] = 0.0

    shifts = np.cumsum(shifts)
    return _slope_level_row_shifts(shifts)


def _vandermonde(x: np.ndarray, degree: int) -> np.ndarray:
    return np.vander(np.asarray(x, dtype=np.float64), N=degree + 1, increasing=True)


def _row_level_poly(
    data: np.ndarray,
    mask: np.ndarray | None,
    masking: str,
    degree: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    yres, xres = data.shape
    corrected = data.copy()
    background = np.zeros_like(corrected)
    shifts = np.zeros(yres, dtype=np.float64)

    if yres == 0 or xres == 0:
        return corrected, background, shifts

    xc = 0.5 * (xres - 1)
    avg = float(data.mean())
    x_all = np.arange(xres, dtype=np.float64) - xc
    design_all = _vandermonde(x_all, degree)

    for i in range(yres):
        row = data[i]
        row_mask = None if mask is None else mask[i]

        valid = apply_masking(row, row_mask, masking)

        coeffs = np.zeros(degree + 1, dtype=np.float64)
        if np.count_nonzero(valid) > degree:
            design = design_all[valid]
            coeffs, _, _, _ = np.linalg.lstsq(design, row[valid], rcond=None)

        coeffs[0] -= avg
        row_background = design_all @ coeffs
        corrected[i] = row - row_background
        background[i] = row_background
        shifts[i] = coeffs[0]

    return corrected, background, shifts


def _calculate_segment_correction(upper: np.ndarray, middle: np.ndarray, lower: np.ndarray) -> np.ndarray:
    length = upper.size
    if length < 4:
        return np.zeros(length, dtype=np.float64)

    corr = float(np.mean((upper + lower) / 2.0 - middle))
    return (3.0 * corr + (upper + lower) / 2.0 - middle) / 4.0


def _line_correct_step_iter(data: np.ndarray) -> np.ndarray:
    yres, xres = data.shape
    if yres < 3 or xres == 0:
        return data.copy()

    corrections = np.zeros_like(data)
    vertical_diff_energy = float(np.mean((data[1:] - data[:-1]) ** 2))
    if vertical_diff_energy <= 0.0:
        return data.copy()

    threshold = 3.0
    for i in range(yres - 2):
        upper = data[i]
        middle = data[i + 1]
        lower = data[i + 2]
        marker_row = corrections[i + 1]

        candidates = (middle - upper) * (middle - lower) > threshold * vertical_diff_energy
        if np.any(candidates):
            signs = np.where(2.0 * middle[candidates] - upper[candidates] - lower[candidates] > 0.0, 1.0, -1.0)
            marker_row[candidates] = signs

        segment_start = 0
        while segment_start < xres:
            sign = marker_row[segment_start]
            if sign == 0.0:
                segment_start += 1
                continue

            segment_end = segment_start + 1
            while segment_end < xres and marker_row[segment_end] == sign:
                segment_end += 1

            marker_row[segment_start:segment_end] = _calculate_segment_correction(
                upper[segment_start:segment_end],
                middle[segment_start:segment_end],
                lower[segment_start:segment_end],
            )
            segment_start = segment_end

    return data + corrections


def _conservative_filter(data: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return data.copy()

    from scipy.ndimage import maximum_filter, minimum_filter

    footprint = np.ones((size, size), dtype=bool)
    footprint[size // 2, size // 2] = False
    min_neighbours = minimum_filter(data, footprint=footprint, mode="nearest")
    max_neighbours = maximum_filter(data, footprint=footprint, mode="nearest")
    return np.clip(data, min_neighbours, max_neighbours)


def _line_correct_step(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    corrected = data.copy()
    avg = float(corrected.mean())

    shifts = _find_row_shifts_trimmed_mean(corrected, None, "ignore", 0.5, 0)
    corrected -= shifts[:, np.newaxis]
    corrected = _line_correct_step_iter(corrected)
    corrected = _line_correct_step_iter(corrected)
    corrected = _conservative_filter(corrected, 5)
    corrected += avg - float(corrected.mean())

    background = data - corrected
    step_shifts = background.mean(axis=1) if background.size else np.zeros(data.shape[0], dtype=np.float64)
    return corrected, step_shifts


def _line_axis(length: int, real_extent: float) -> np.ndarray | None:
    if length <= 0:
        return None
    return np.linspace(0.0, float(real_extent), int(length), dtype=np.float64)


@register_node(display_name="Line Correction")
class LineCorrection:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": ([
                    "median",
                    "median_diff",
                    "trimmed_mean",
                    "trimmed_diff",
                    "polynomial",
                    "step",
                ], {"default": "median"}),
                "direction": (["horizontal", "vertical"], {"default": "horizontal"}),
                "masking": (["ignore", "include", "exclude"], {"default": "ignore"}),
                "trim_fraction": ("FLOAT", {
                    "default": 0.05,
                    "min": 0.0,
                    "max": 0.5,
                    "step": 0.01,
                    "show_when_widget_value": {"method": ["trimmed_mean", "trimmed_diff"]},
                }),
                "polynomial_degree": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 5,
                    "step": 1,
                    "show_when_widget_value": {"method": ["polynomial"]},
                }),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
        ('DATA_FIELD', 'background'),
        ('LINE', 'row_shifts'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Correct scan-line mismatches using Gwyddion-derived row alignment methods. "
        "Supports median and trimmed row alignment, difference-based alignment, polynomial row leveling, "
        "and the step-line correction path from Gwyddion's linecorrect/linematch modules."
    )

    def process(
        self,
        field: DataField,
        method: str,
        direction: str,
        masking: str,
        trim_fraction: float,
        polynomial_degree: int,
        mask: np.ndarray | None = None,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        mask_array = normalize_mask(mask, data.shape)

        if direction not in {"horizontal", "vertical"}:
            raise ValueError(f"Unknown direction: {direction}")

        working = data.copy()
        working_mask = None if mask_array is None else mask_array.copy()
        if direction == "vertical":
            working = working.T
            if working_mask is not None:
                working_mask = working_mask.T

        if method == "median":
            shifts = _find_row_shifts_trimmed_mean(working, working_mask, masking, 0.5, 0)
            corrected = working - shifts[:, np.newaxis]
            background = np.broadcast_to(shifts[:, np.newaxis], working.shape).copy()
        elif method == "median_diff":
            shifts = _find_row_shifts_trimmed_diff(working, working_mask, masking, 0.5, 0)
            corrected = working - shifts[:, np.newaxis]
            background = np.broadcast_to(shifts[:, np.newaxis], working.shape).copy()
        elif method == "trimmed_mean":
            shifts = _find_row_shifts_trimmed_mean(working, working_mask, masking, float(trim_fraction), 0)
            corrected = working - shifts[:, np.newaxis]
            background = np.broadcast_to(shifts[:, np.newaxis], working.shape).copy()
        elif method == "trimmed_diff":
            shifts = _find_row_shifts_trimmed_diff(working, working_mask, masking, float(trim_fraction), 0)
            corrected = working - shifts[:, np.newaxis]
            background = np.broadcast_to(shifts[:, np.newaxis], working.shape).copy()
        elif method == "polynomial":
            corrected, background, shifts = _row_level_poly(
                working,
                working_mask,
                masking,
                int(polynomial_degree),
            )
        elif method == "step":
            corrected, shifts = _line_correct_step(working)
            background = working - corrected
        else:
            raise ValueError(f"Unknown line correction method: {method}")

        if direction == "vertical":
            corrected = corrected.T
            background = background.T
            line_axis = _line_axis(field.xres, field.xreal)
        else:
            line_axis = _line_axis(field.yres, field.yreal)

        corrected_field = field.replace(data=corrected)
        background_field = field.replace(data=background)
        shift_line = LineData(
            data=np.asarray(shifts, dtype=np.float64),
            x_axis=line_axis,
            x_unit=field.si_unit_xy,
            y_unit=field.si_unit_z,
        )

        return (corrected_field, background_field, shift_line)
