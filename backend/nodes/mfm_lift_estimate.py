"""MFM Lift Estimate — estimate the lift height difference between two MFM images."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


def _frequency_magnitudes(xres: int, yres: int, xreal: float, yreal: float) -> np.ndarray:
    """Spatial frequency magnitudes |k| in cycles/m, FFT (not humanized) arrangement."""
    kx = np.fft.fftfreq(xres, d=xreal / xres)
    ky = np.fft.fftfreq(yres, d=yreal / yres)
    KX, KY = np.meshgrid(kx, ky)
    return np.sqrt(KX * KX + KY * KY)


def _mfm_shift_z(data: np.ndarray, xreal: float, yreal: float, zdiff: float) -> np.ndarray:
    """Shared FFT lift-shift kernel (see gwy_data_field_mfm_shift_z in libprocess/mfm.c)."""
    K = _frequency_magnitudes(data.shape[1], data.shape[0], xreal, yreal)
    ztf = np.exp(-2.0 * np.pi * K * zdiff)
    return np.real(np.fft.ifft2(np.fft.fft2(data) * ztf))


def _interpolate_parabolic(xy):
    """Port of the static interpolate_parabolic() in libgwyddion/gwymath.c."""
    u1 = (xy[1][0] - xy[0][0]) * (xy[2][1] - xy[1][1])
    u2 = (xy[2][0] - xy[1][0]) * (xy[0][1] - xy[1][1])
    if abs(u2 + u1) <= 1e-12 * (abs(u1) + abs(u2)):
        return None
    tx = 0.5 * (xy[1][0] + (u2 * xy[2][0] + u1 * xy[0][0]) / (u2 + u1))
    if tx <= xy[0][0] or tx >= xy[2][0]:
        return None
    return tx


def _min_in_array(xy, n):
    """Port of find_min_in_array() in libgwyddion/gwymath.c: index of the minimum
    value among points 1..n (point 0 excluded), plus a flag telling whether the
    minimum is distinct from its neighbours.  As in the C code, the array has 13
    slots and slot n may hold stale data from an earlier iteration."""
    any_variation = False
    imin = n // 2
    for i in range(1, n + 1):
        if xy[i][1] < xy[imin][1]:
            imin = i
    y = xy[imin][1]
    if imin > 0:
        yy = xy[imin - 1][1]
        if yy - y > 6e-16 * (abs(y) + abs(yy)):
            any_variation = True
    if imin + 1 < n:
        yy = xy[imin + 1][1]
        if yy - y > 6e-16 * (abs(y) + abs(yy)):
            any_variation = True
    return imin, any_variation


def _find_minimum_1d(function, a, b):
    """Port of gwy_math_find_minimum_1d (libgwyddion/gwymath.c): 12-point initial
    scan followed by bisection/parabolic-interpolation bracket refinement (at most
    50 iterations).  The edge flags are sticky, exactly as in the C code."""
    initial_n = 12
    if a > b:
        a, b = b, a
    if b - a < 1.2e-16 * (abs(a) + abs(b)):
        return 0.5 * (a + b)

    # 13-slot array, mirroring GwyXY xy[initial_n+1].
    xy = [(0.0, 0.0)] * (initial_n + 1)
    xy[0] = (a, function(a))
    for i in range(1, initial_n + 1):
        x = b if i == initial_n else b / initial_n * i + a / initial_n * (initial_n - i)
        xy[i] = (x, function(x))

    imin, any_variation = _min_in_array(xy, initial_n)
    if not any_variation:
        return 0.5 * (a + b)

    at_left_edge = at_right_edge = False
    _memmove_xy(xy, imin - 1)

    iter_ = 0
    eps = 1.2e-15
    while xy[2][0] - xy[0][0] > eps * (abs(xy[0][0]) + abs(xy[2][0])):
        n = 3
        if at_left_edge:
            xy[n] = (0.8 * xy[0][0] + 0.2 * xy[1][0], 0.0)
            n += 1
        elif at_right_edge:
            xy[n] = (0.2 * xy[1][0] + 0.8 * xy[2][0], 0.0)
            n += 1
        else:
            if xy[1][0] - xy[0][0] >= xy[2][0] - xy[1][0]:
                xy[n] = (0.2 * xy[0][0] + 0.8 * xy[1][0], 0.0)
                n += 1
            else:
                xy[n] = (0.8 * xy[1][0] + 0.2 * xy[2][0], 0.0)
                n += 1

            x = _interpolate_parabolic(xy[:3])
            if x is not None:
                xeps = eps * abs(x)
                if x - xy[0][0] > xeps and xy[2][0] - x > xeps and abs(x - xy[3][0]) > xeps:
                    xy[n] = (x, 0.0)
                    n += 1

        for i in range(3, n):
            xy[i] = (xy[i][0], function(xy[i][0]))

        # qsort by x of the first n points only.
        xy[:n] = sorted(xy[:n], key=lambda p: p[0])

        imin, any_variation = _min_in_array(xy, n)
        if not any_variation:
            return xy[imin][0]

        if imin == 0:
            at_left_edge = True
        elif imin == n - 1:
            at_right_edge = True
            _memmove_xy(xy, n - 3)
        else:
            _memmove_xy(xy, imin - 1)

        iter_ += 1
        if iter_ == 50:
            break

    return xy[1][0]


def _memmove_xy(xy, start):
    """memmove(xy, xy + start, 3*sizeof(GwyXY)): shift the 3-point window to
    xy[0..2], leaving the remaining slots (3..12 + the source slots) untouched."""
    xy[0], xy[1], xy[2] = xy[start], xy[start + 1], xy[start + 2]


def _mfm_find_shift_z(data1, data2, xreal, yreal, zdiffmin, zdiffmax):
    """Port of gwy_data_field_mfm_find_shift_z (libprocess/mfm.c): minimise
    ||shift_z(field1, z) - field2||^2 over z in [zdiffmin, zdiffmax]."""
    K = _frequency_magnitudes(data1.shape[1], data1.shape[0], xreal, yreal)
    f1 = np.fft.fft2(data1)
    f2 = np.fft.fft2(data2)
    re1, im1 = f1.real, f1.imag
    re2, im2 = f2.real, f2.imag

    def residuum(zshift):
        ztf = np.exp(-2.0 * np.pi * K * zshift)
        dre = ztf * re1 - re2
        dim = ztf * im1 - im2
        return float(np.sum(dre * dre + dim * dim))

    return _find_minimum_1d(residuum, zdiffmin, zdiffmax)


@register_node(display_name="MFM Lift Estimate")
class MFMLiftEstimate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "shifted": ("DATA_FIELD",),
                "start": ("FLOAT", {
                    "default": 10e-9, "min": -1e-6, "max": 1e-6, "step": 1e-9,
                }),
                "stop": ("FLOAT", {
                    "default": 20e-9, "min": -1e-6, "max": 1e-6, "step": 1e-9,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'estimated'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    CATEGORY = "SPM"

    DESCRIPTION = (
        "Estimates the lift height difference between two MFM images of the same "
        "area measured at different heights. The estimate minimises the squared "
        "difference between the second image and the first image propagated with "
        "the FFT transfer function exp(-2*pi*|k|*z); a positive result means the "
        "second image was measured at a larger lift height. Ports Gwyddion's "
        "mfm_findshift module (gwy_data_field_mfm_find_shift_z). The output field "
        "is the residual after applying the estimated shift."
    )

    KEYWORDS = ("magnetic", "mfM", "lift", "estimate", "height", "shift", "fft")

    def process(self, field: DataField, shifted: DataField, start: float, stop: float) -> tuple:
        data1 = np.asarray(field.data, dtype=np.float64)
        data2 = np.asarray(shifted.data, dtype=np.float64)
        if data1.shape != data2.shape:
            raise ValueError(
                f"Both fields must have the same resolution, got {data1.shape} and {data2.shape}"
            )

        minshift = _mfm_find_shift_z(data1, data2, field.xreal, field.yreal,
                                     float(start), float(stop))
        difference = _mfm_shift_z(data1, field.xreal, field.yreal, minshift) - data2

        lo, hi = sorted((float(start), float(stop)))
        table = RecordTable([
            {"quantity": "Estimated lift shift", "value": float(minshift), "unit": "m"},
            {"quantity": "Search range from", "value": lo, "unit": "m"},
            {"quantity": "Search range to", "value": hi, "unit": "m"},
        ])
        emit_table(table)

        return (field.replace(data=difference), table)
