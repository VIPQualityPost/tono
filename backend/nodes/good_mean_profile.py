"""Good Mean Profile — robust average row profile.

Calculates a good average row profile from one image (trimmed mean of each
column over all scan rows) or from two images of repeated scanning of the
same feature (mean image with a percentile-based outlier rejection).  The
corrected field replaces out-of-band pixels with the good profile value.
"""

from __future__ import annotations

import numpy as np

from backend.data_types import DataField, LineData
from backend.node_registry import register_node


def _trimmed_mean(values: np.ndarray, ntrim: int) -> float:
    """Mean of *values* with *ntrim* lowest and highest samples discarded."""
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return 0.0
    n = values.size
    if 2 * ntrim >= n:
        return float(values.mean())
    sorted_values = np.sort(values, kind="mergesort")
    return float(sorted_values[ntrim:n - ntrim].mean())


def _kth_ranks(values: np.ndarray, k0: int, k1: int) -> tuple[float, float]:
    """Values at 0-based ranks k0 and k1."""
    values = np.asarray(values, dtype=np.float64)
    n = values.size
    if n == 0:
        return (0.0, 0.0)
    k0 = max(0, min(int(k0), n - 1))
    k1 = max(0, min(int(k1), n - 1))
    if k0 == k1:
        v = float(np.partition(values, k0)[k0])
        return (v, v)
    out = np.partition(values, [k0, k1])
    return (float(out[k0]), float(out[k1]))


def _good_profile_single(
    data: np.ndarray,
    trim_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-column trimmed means and the low/high outlier band.

    Port of good_profile_do_single(): the field is processed column by column
    with ntrim = round(0.5*trim_fraction*yres) samples trimmed on each side;
    low/high are the rank-ntrim and rank-(yres-1-ntrim) column values.
    """
    yres, xres = data.shape
    ntrim = int(np.rint(0.5 * trim_fraction * yres))
    if 2 * ntrim + 1 > yres:
        ntrim = (yres - 1) // 2

    profile = np.empty(xres, dtype=np.float64)
    low = np.empty(xres, dtype=np.float64)
    high = np.empty(xres, dtype=np.float64)
    for j in range(xres):
        col = data[:, j]
        profile[j] = _trimmed_mean(col, ntrim)
        low[j], high[j] = _kth_ranks(col, ntrim, yres - 1 - ntrim)
    return profile, low, high


def _good_profile_multiple(
    d1: np.ndarray,
    d2: np.ndarray,
    trim_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean image, outlier mask and per-column good profile for two images.

    Port of good_profile_do_multiple(): pixels whose |d1D2| exceeds the
    (100*(1-trim_fraction))-th percentile (midpoint interpolation) of all
    absolute differences are rejected; the profile is then the column mean
    of the mean image over the remaining pixels.
    """
    yres, xres = d1.shape
    diff = np.abs(d1 - d2)
    p = 100.0 * (1.0 - trim_fraction)
    threshold = float(np.percentile(diff, p, method="midpoint"))

    outlier = diff > threshold
    mean_image = 0.5 * (d1 + d2)
    valid = ~outlier

    profile = np.empty(xres, dtype=np.float64)
    for j in range(xres):
        col = mean_image[:, j]
        v = valid[:, j]
        profile[j] = float(col[v].mean()) if v.any() else 0.0
    return mean_image, outlier, profile


@register_node(display_name="Good Mean Profile")
class GoodMeanProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mode": (["single", "multiple"], {"default": "single"}),
                "trim_fraction": ("FLOAT", {
                    "default": 0.05,
                    "min": 0.0,
                    "max": 0.9999,
                    "step": 0.01,
                }),
            },
            "optional": {
                "second_field": ("DATA_FIELD",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'corrected'),
        ('LINE', 'profile'),
    )
    FUNCTION = "process"
    CATEGORY = "Level & Correct"

    DESCRIPTION = (
        "Calculate a good mean row profile from one image or from two images "
        "of repeated scanning of the same feature. In single mode each column "
        "is averaged with a trimmed mean; in multiple mode outliers between "
        "the two images are rejected before averaging. Pixels outside the "
        "good-value band are replaced by the profile value in the corrected "
        "field."
    )

    KEYWORDS = ("profile", "mean", "average", "scan", "repeat", "outlier", "trim")

    def process(
        self,
        field: DataField,
        mode: str,
        trim_fraction: float,
        second_field: DataField | None = None,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        if data.ndim != 2:
            raise ValueError("Good Mean Profile requires a 2D data field.")

        if mode == "single":
            profile_array, low, high = _good_profile_single(data, float(trim_fraction))
            band = (data < low[None, :]) | (data > high[None, :])
            corrected_data = data.copy()
            if band.any():
                corrected_data[band] = profile_array[np.nonzero(band)[1]]
        elif mode == "multiple":
            if second_field is None:
                raise ValueError("Good Mean Profile in 'multiple' mode requires a second field.")
            d2 = np.asarray(second_field.data, dtype=np.float64)
            if d2.shape != data.shape:
                raise ValueError(
                    f"Second field shape {d2.shape} does not match first field shape {data.shape}"
                )
            mean_image, outlier, profile_array = _good_profile_multiple(
                data, d2, float(trim_fraction),
            )
            corrected_data = mean_image.copy()
            if outlier.any():
                corrected_data[outlier] = profile_array[np.nonzero(outlier)[1]]
        else:
            raise ValueError(f"Unknown mode: {mode}")

        corrected = field.replace(data=corrected_data)
        x_axis = np.linspace(0.0, float(field.xreal), int(field.xres)) if field.xres else None
        profile = LineData(
            data=profile_array,
            x_axis=x_axis,
            x_unit=field.si_unit_xy,
            y_unit=field.si_unit_z,
        )
        return (corrected, profile)
