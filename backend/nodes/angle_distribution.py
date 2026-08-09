"""Angle Distribution — two-dimensional distribution of angle projections."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _filter_slope(data: np.ndarray, dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """Symmetric differences, one-sided at edges,
    in physical units (divided by the pixel size)."""
    yres, xres = data.shape
    xder = np.zeros_like(data)
    yder = np.zeros_like(data)

    xder[:, 0] = (data[:, 1] - data[:, 0]) / dx
    xder[:, -1] = (data[:, -1] - data[:, -2]) / dx
    if xres > 2:
        xder[:, 1:-1] = (data[:, 2:] - data[:, :-2]) / (2.0 * dx)

    yder[0, :] = (data[1, :] - data[0, :]) / dy
    yder[-1, :] = (data[-1, :] - data[-2, :]) / dy
    if yres > 2:
        yder[1:-1, :] = (data[2:, :] - data[:-2, :]) / (2.0 * dy)
    return xder, yder


def _fit_local_plane_slopes(data: np.ndarray, size: int,
                            dx: float, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """Local plane fit with the 1/dx, 1/dy slope scaling. Fits a plane z = c + bx*x
    + by*y through each clamped neighbourhood and returns bx/dx, by/dy."""
    yres, xres = data.shape
    xder = np.zeros((yres, xres), dtype=np.float64)
    yder = np.zeros((yres, xres), dtype=np.float64)
    # as in the C: the shift moves the origin to the sample pixel; for even sizes
    # the neighbourhood sticks to the right, giving the extra 0.5.
    asym = (1 - size % 2) / 2.0
    half_lo = (size - 1) // 2
    half_hi = size // 2

    for i in range(yres):
        ifrom = max(0, i - half_lo)
        ito = min(yres - 1, i + half_hi)
        if ifrom == ito and ifrom:
            ifrom -= 1
        for j in range(xres):
            jfrom = max(0, j - half_lo)
            jto = min(xres - 1, j + half_hi)
            if jfrom == jto and jfrom:
                jfrom -= 1
            rect = data[ifrom:ito + 1, jfrom:jto + 1]
            hh = ito - ifrom
            ww = jto - jfrom
            rows = np.arange(hh + 1, dtype=np.float64)
            cols = np.arange(ww + 1, dtype=np.float64)
            sumz = float(rect.sum())
            n = (hh + 1) * (ww + 1)
            sumx = n * ww / 2.0
            sumy = n * hh / 2.0
            sumxx = sumx * (2 * ww + 1) / 3.0
            sumyy = sumy * (2 * hh + 1) / 3.0
            sumxy = sumx * sumy / n
            sumzx = float(np.sum(rect * cols[None, :]))
            sumzy = float(np.sum(rect * rows[:, None]))
            sumzz = float(np.sum(rect * rect))

            # Move origin to the pixel, including in z (remembering the mean).
            shift = ifrom - (i + asym)
            sumxy += shift * sumx
            sumyy += shift * (2 * sumy + n * shift)
            sumzy += shift * sumz
            sumy += n * shift
            shift = jfrom - (j + asym)
            sumxx += shift * (2 * sumx + n * shift)
            sumxy += shift * sumy
            sumzx += shift * sumz
            sumx += n * shift
            shift = -sumz / n
            sumzx += shift * sumx
            sumzy += shift * sumy
            sumzz += shift * (2 * sumz + n * shift)

            det = sumxx * sumyy - sumxy * sumxy
            if det == 0.0:
                continue
            bx = (sumzx * sumyy - sumxy * sumzy) / det
            by = (sumzy * sumxx - sumxy * sumzx) / det
            xder[i, j] = bx / dx
            yder[i, j] = by / dy
    return xder, yder


def _angle_distribution(data: np.ndarray, size: int, steps: int,
                        logscale: bool, fit_plane: bool, kernel_size: int,
                        dx: float, dy: float) -> tuple[np.ndarray, dict]:
    """Port of angle_dist.c count_angles()/make_datafield(). Returns the 2-D count
    histogram and measurement statistics (slope magnitude statistics in radians)."""
    if fit_plane:
        xder, yder = _fit_local_plane_slopes(data, kernel_size, dx, dy)
    else:
        xder, yder = _filter_slope(data, dx, dy)

    slop2 = xder * xder + yder * yder
    maxslope = float(np.sqrt(np.max(slop2)))
    maxangle = float(np.arctan(maxslope))
    if maxslope <= 0.0 or not np.isfinite(maxangle) or maxangle <= 0.0:
        counts = np.zeros((size, size), dtype=np.float64)
        stats = {"mean": 0.0, "std": 0.0, "max": 0.0}
        return counts, stats

    d = np.arctan(np.sqrt(slop2))
    phi = np.arctan2(yder, xder)

    mean_angle = float(np.mean(d))
    std_angle = float(np.sqrt(np.mean(d * d) - mean_angle * mean_angle))

    counts = np.zeros((size, size), dtype=np.float64)
    theta = 2.0 * np.pi * np.arange(steps, dtype=np.float64) / float(steps)
    ct = np.cos(theta)
    st = np.sin(theta)
    for j in range(steps):
        v = d * np.cos(theta[j] - phi)
        xider = np.floor(size * (v * ct[j] / (2.0 * maxangle) + 0.5))
        yider = np.floor(size * (v * st[j] / (2.0 * maxangle) + 0.5))
        xider = np.clip(xider, 0, size - 1).astype(np.intp)
        yider = np.clip(yider, 0, size - 1).astype(np.intp)
        np.add.at(counts, (yider, xider), 1.0)

    if logscale:
        with np.errstate(divide="ignore"):
            counts = np.where(counts > 0.0, np.log(counts) + 1.0, 0.0)

    stats = {"mean": float(mean_angle), "std": float(std_angle), "max": float(maxangle)}
    return counts, stats


@register_node(display_name="Angle Distribution")
class AngleDistribution:
    CATEGORY = "Measure"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "size": ("INT", {"default": 200, "min": 1, "max": 1024, "step": 1}),
                "steps": ("INT", {"default": 360, "min": 1, "max": 65536, "step": 1}),
                "logscale": ("BOOLEAN", {"default": False}),
                "fit_plane": ("BOOLEAN", {"default": False}),
                "kernel_size": ("INT", {"default": 5, "min": 2, "max": 16, "step": 1}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'distribution'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Calculate the two-dimensional distribution of angle projections: for every "
        "pixel the slope vector is projected onto a "
        "set of directions and accumulated into a polar histogram, giving the "
        "distribution of surface-angle projections. Slopes are computed with simple "
        "symmetric differences, or optionally by local plane fitting with a given "
        "kernel size. The measurement table reports the mean, standard deviation and "
        "maximum of the local slope angle."
    )

    KEYWORDS = ("angle distribution", "slope", "histogram", "orientation", "facets")

    def process(self, field: DataField, size: int, steps: int, logscale: bool,
                fit_plane: bool, kernel_size: int) -> tuple:
        size = int(size)
        steps = int(steps)
        kernel_size = int(kernel_size)
        if size < 1 or steps < 1:
            raise ValueError("Output size and number of steps must be at least 1.")
        data = np.asarray(field.data, dtype=np.float64)
        dx = field.dx if field.xres else 1.0
        dy = field.dy if field.yres else 1.0

        counts, stats = _angle_distribution(data, size, steps, logscale, fit_plane,
                                            kernel_size, dx, dy)

        rows = [
            {"quantity": "Mean slope angle", "value": stats["mean"], "unit": "rad"},
            {"quantity": "Std slope angle", "value": stats["std"], "unit": "rad"},
            {"quantity": "Max slope angle", "value": stats["max"], "unit": "rad"},
        ]
        measurement = RecordTable(rows)
        emit_table(measurement)

        distribution = DataField(
            data=counts,
            xreal=float(2.0 * np.pi),
            yreal=float(2.0 * np.pi),
            xoff=float(-np.pi),
            yoff=float(-np.pi),
            si_unit_xy="rad",
            si_unit_z="",
            domain="spatial",
            colormap=field.colormap,
        )
        return (distribution, measurement)
