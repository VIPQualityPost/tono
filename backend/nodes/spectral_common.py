from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.nodes.helpers import _square_unit


def _level_data(data: np.ndarray, level: str) -> np.ndarray:
    leveled = np.asarray(data, dtype=np.float64).copy()
    yres, xres = leveled.shape

    if level == "none":
        return leveled

    if level == "mean":
        leveled -= float(np.mean(leveled))
        return leveled

    if level == "plane":
        yy, xx = np.mgrid[0:yres, 0:xres]
        design = np.column_stack([
            np.ones(xres * yres, dtype=np.float64),
            xx.ravel().astype(np.float64),
            yy.ravel().astype(np.float64),
        ])
        coeffs, _, _, _ = np.linalg.lstsq(design, leveled.ravel(), rcond=None)
        plane = coeffs[0] + coeffs[1] * xx + coeffs[2] * yy
        leveled -= plane
        return leveled

    raise ValueError(f"Unsupported levelling mode: {level}")


def _window_vector(size: int, windowing: str) -> np.ndarray:
    if size <= 0:
        return np.ones(0, dtype=np.float64)

    t = (np.arange(size, dtype=np.float64) + 0.5) / float(size)

    if windowing == "none":
        return np.ones(size, dtype=np.float64)
    if windowing == "hann":
        return 0.5 - 0.5 * np.cos(2.0 * np.pi * t)
    if windowing == "hamming":
        return 0.54 - 0.46 * np.cos(2.0 * np.pi * t)
    if windowing == "blackman":
        return 0.42 - 0.5 * np.cos(2.0 * np.pi * t) + 0.08 * np.cos(4.0 * np.pi * t)

    raise ValueError(f"Unsupported windowing mode: {windowing}")


def _apply_window_with_rms_compensation(data: np.ndarray, windowing: str) -> np.ndarray:
    windowed = np.asarray(data, dtype=np.float64).copy()
    if windowing == "none":
        return windowed

    rms = float(np.sqrt(np.mean(windowed**2)))
    wy = _window_vector(windowed.shape[0], windowing)
    wx = _window_vector(windowed.shape[1], windowing)
    windowed *= np.outer(wy, wx)

    new_rms = float(np.sqrt(np.mean(windowed**2)))
    if rms > 0.0 and new_rms > 0.0:
        windowed *= rms / new_rms

    return windowed


def preprocess_spectral_data(field: DataField, *, level: str, windowing: str = "none") -> np.ndarray:
    leveled = _level_data(field.data, level)
    return _apply_window_with_rms_compensation(leveled, windowing)


def _inverse_unit(unit: str) -> str:
    text = str(unit or "").strip()
    if not text:
        return ""
    return f"1/{text}"


def _product_unit(*units: str) -> str:
    parts = [str(unit).strip() for unit in units if str(unit or "").strip()]
    return " ".join(parts)


def spatial_frequency_field(field: DataField, data: np.ndarray) -> DataField:
    return DataField(
        data=np.asarray(data, dtype=np.float64),
        xreal=float(field.xres / field.xreal),
        yreal=float(field.yres / field.yreal),
        xoff=float(-0.5 * field.xres / field.xreal),
        yoff=float(-0.5 * field.yres / field.yreal),
        si_unit_xy=_inverse_unit(field.si_unit_xy),
        si_unit_z=field.si_unit_z,
        domain="frequency",
        colormap=field.colormap,
    )


def psdf_field_from_data(field: DataField, data: np.ndarray) -> DataField:
    transformed = np.fft.fftshift(np.fft.fft2(np.asarray(data, dtype=np.float64)))
    magnitude = np.abs(transformed)
    n = field.xres * field.yres
    psdf = (magnitude**2) * field.dx * field.dy / (float(n) * 4.0 * np.pi**2)
    xreal = float(2.0 * np.pi / field.dx)
    yreal = float(2.0 * np.pi / field.dy)

    return DataField(
        data=psdf,
        xreal=xreal,
        yreal=yreal,
        xoff=float(-0.5 * xreal),
        yoff=float(-0.5 * yreal),
        si_unit_xy=_inverse_unit(field.si_unit_xy),
        si_unit_z=_product_unit(_square_unit(field.si_unit_z), _square_unit(field.si_unit_xy)),
        domain="frequency",
        colormap=field.colormap,
    )


def acf_line_from_data(profile, data: np.ndarray, *, nrange: int = 0):
    from scipy.signal import fftconvolve
    from backend.data_types import LineData

    z = np.asarray(data, dtype=np.float64).ravel()
    n = len(z)
    nrange = int(nrange) if nrange else max(1, n // 2)
    nrange = max(1, min(nrange, n))

    corr_full = fftconvolve(z, z[::-1], mode="full")
    center = n - 1
    corr = corr_full[center - (nrange - 1):center + nrange]

    counts = np.array([n - abs(lag) for lag in range(-(nrange - 1), nrange)], dtype=np.float64)
    acf = corr / counts

    x_unit = profile.x_unit if hasattr(profile, "x_unit") else ""
    y_unit = _square_unit(profile.y_unit) if hasattr(profile, "y_unit") and profile.y_unit else ""

    if hasattr(profile, "x_axis") and profile.x_axis is not None and len(profile.x_axis) > 1:
        d = float(profile.x_axis[1] - profile.x_axis[0])
    else:
        d = 1.0

    lag_axis = np.arange(-(nrange - 1), nrange, dtype=np.float64) * d

    return LineData(data=acf, x_axis=lag_axis, x_unit=x_unit, y_unit=y_unit)


def acf_field_from_data(field: DataField, data: np.ndarray, *, xrange: int = 0, yrange: int = 0) -> DataField:
    from scipy.signal import fftconvolve

    source = np.asarray(data, dtype=np.float64)
    yres, xres = source.shape
    xrange = int(xrange) if xrange else max(1, xres // 2)
    yrange = int(yrange) if yrange else max(1, yres // 2)
    xrange = max(1, min(xrange, xres))
    yrange = max(1, min(yrange, yres))

    corr_full = fftconvolve(source, source[::-1, ::-1], mode="full")
    cy = yres - 1
    cx = xres - 1
    corr = corr_full[cy - (yrange - 1):cy + yrange, cx - (xrange - 1):cx + xrange]

    count_x = np.array([xres - abs(dx) for dx in range(-(xrange - 1), xrange)], dtype=np.float64)
    count_y = np.array([yres - abs(dy) for dy in range(-(yrange - 1), yrange)], dtype=np.float64)
    counts = np.outer(count_y, count_x)
    acf = corr / counts

    txres = 2 * xrange - 1
    tyres = 2 * yrange - 1
    xreal = float(field.xreal * txres / field.xres)
    yreal = float(field.yreal * tyres / field.yres)

    return DataField(
        data=np.asarray(acf, dtype=np.float64),
        xreal=xreal,
        yreal=yreal,
        xoff=float(-0.5 * xreal),
        yoff=float(-0.5 * yreal),
        si_unit_xy=field.si_unit_xy,
        si_unit_z=_square_unit(field.si_unit_z),
        domain="spatial",
        colormap=field.colormap,
    )
