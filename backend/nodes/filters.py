"""
Filter nodes — Gwyddion-equivalent image filters.

Gwyddion equivalents:
  GaussianFilter  → gwy_data_field_filter_gaussian
  MedianFilter    → gwy_data_field_filter_median
  EdgeDetect      → gwy_data_field_filter_sobel / laplacian / log
  FFTFilter1D     → fft_filter_1d.c (bandpass/lowpass/highpass on LINE profiles)
  FFTFilter2D     → fft_filter_2d.c (frequency-domain filtering of DATA_FIELDs)
"""

from __future__ import annotations
from functools import lru_cache
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, LineData


# ---------------------------------------------------------------------------
# GaussianFilter
# ---------------------------------------------------------------------------

@register_node(display_name="Gaussian Filter")
class GaussianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 50.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = "Apply a Gaussian blur. Equivalent to gwy_data_field_filter_gaussian."

    def process(self, field: DataField, sigma: float) -> tuple:
        from scipy.ndimage import gaussian_filter
        data = gaussian_filter(field.data, sigma=float(sigma))
        return (field.replace(data=data),)


# ---------------------------------------------------------------------------
# MedianFilter
# ---------------------------------------------------------------------------

@register_node(display_name="Median Filter")
class MedianFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "size": ("INT", {"default": 3, "min": 1, "max": 21, "step": 2}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = "Apply a median filter. Equivalent to gwy_data_field_filter_median."

    def process(self, field: DataField, size: int) -> tuple:
        from scipy.ndimage import median_filter
        size = max(1, int(size))
        data = median_filter(field.data, size=size)
        return (field.replace(data=data),)


# ---------------------------------------------------------------------------
# EdgeDetect
# ---------------------------------------------------------------------------

@register_node(display_name="Edge Detect")
class EdgeDetect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["sobel", "prewitt", "laplacian", "log"],),
                "sigma": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("edges",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = (
        "Detect edges using Sobel, Prewitt, Laplacian, or LoG operators. "
        "Equivalent to gwy_data_field_filter_sobel / gwy_data_field_filter_laplacian."
    )

    def process(self, field: DataField, method: str, sigma: float) -> tuple:
        from scipy.ndimage import sobel, prewitt, gaussian_laplace, laplace
        data = field.data

        if method == "sobel":
            sx = sobel(data, axis=1)
            sy = sobel(data, axis=0)
            result = np.hypot(sx, sy)
        elif method == "prewitt":
            px = prewitt(data, axis=1)
            py = prewitt(data, axis=0)
            result = np.hypot(px, py)
        elif method == "laplacian":
            result = laplace(data)
        elif method == "log":
            result = gaussian_laplace(data, sigma=float(sigma))
        else:
            raise ValueError(f"Unknown edge detection method: {method}")

        return (field.replace(data=result),)


# ---------------------------------------------------------------------------
# Butterworth transfer function helpers
# ---------------------------------------------------------------------------

def _butterworth_lp(freq: np.ndarray, cutoff: float, order: int) -> np.ndarray:
    """Butterworth lowpass: H = 1 / (1 + (f/fc)^(2n))."""
    with np.errstate(divide="ignore", over="ignore"):
        return 1.0 / (1.0 + (freq / cutoff) ** (2 * order))


def _butterworth_hp(freq: np.ndarray, cutoff: float, order: int) -> np.ndarray:
    """Butterworth highpass: H = 1 / (1 + (fc/f)^(2n))."""
    with np.errstate(divide="ignore", invalid="ignore"):
        h = 1.0 / (1.0 + (cutoff / freq) ** (2 * order))
    h = np.where(np.isfinite(h), h, 0.0)
    return h


def _build_1d_transfer(n: int, filter_type: str, cutoff: float,
                       cutoff_high: float, order: int) -> np.ndarray:
    """Build a 1-D transfer function for an FFT of length *n*.

    Frequencies are normalised so that 1.0 = Nyquist (fs/2).
    The returned array has the same layout as np.fft.rfft output (length n//2+1).
    """
    freq = np.linspace(0, 1, n // 2 + 1)

    if filter_type == "lowpass":
        H = _butterworth_lp(freq, cutoff, order)
    elif filter_type == "highpass":
        H = _butterworth_hp(freq, cutoff, order)
    elif filter_type == "bandpass":
        H = _butterworth_hp(freq, cutoff, order) * _butterworth_lp(freq, cutoff_high, order)
    elif filter_type == "notch":
        bp = _butterworth_hp(freq, cutoff, order) * _butterworth_lp(freq, cutoff_high, order)
        H = 1.0 - bp
    else:
        H = np.ones_like(freq)
    return H


@lru_cache(maxsize=64)
def _cached_1d_transfer(n: int, filter_type: str, cutoff: float,
                        cutoff_high: float, order: int) -> np.ndarray:
    transfer = _build_1d_transfer(n, filter_type, cutoff, cutoff_high, order)
    transfer.setflags(write=False)
    return transfer


@lru_cache(maxsize=32)
def _fft_radius_grid(yres: int, xres: int) -> np.ndarray:
    fy = np.fft.fftfreq(yres)[:, np.newaxis] * 2.0
    fx = np.fft.rfftfreq(xres)[np.newaxis, :] * 2.0
    radius = np.sqrt(fx * fx + fy * fy) / np.sqrt(2.0)
    np.clip(radius, 0.0, 1.0, out=radius)
    radius.setflags(write=False)
    return radius


@lru_cache(maxsize=128)
def _cached_2d_transfer(yres: int, xres: int, filter_type: str,
                        cutoff: float, cutoff_high: float, order: int) -> np.ndarray:
    radius = _fft_radius_grid(yres, xres)

    if filter_type == "lowpass":
        transfer = _butterworth_lp(radius, cutoff, order)
    elif filter_type == "highpass":
        transfer = _butterworth_hp(radius, cutoff, order)
    elif filter_type == "bandpass":
        transfer = _butterworth_hp(radius, cutoff, order) * _butterworth_lp(radius, cutoff_high, order)
    elif filter_type == "notch":
        band = _butterworth_hp(radius, cutoff, order) * _butterworth_lp(radius, cutoff_high, order)
        transfer = 1.0 - band
    else:
        transfer = np.ones_like(radius)

    transfer.setflags(write=False)
    return transfer


# ---------------------------------------------------------------------------
# FFTFilter1D — frequency-domain filtering of LINE profiles
# ---------------------------------------------------------------------------

@register_node(display_name="1D FFT Filter")
class FFTFilter1D:
    """Bandpass / lowpass / highpass / notch filtering of 1-D line profiles.

    Equivalent to Gwyddion's fft_filter_1d module.  Uses a Butterworth
    transfer function with configurable order for a smooth roll-off.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line": ("LINE",),
                "filter_type": (["lowpass", "highpass", "bandpass", "notch"],),
                "cutoff": ("FLOAT", {
                    "default": 0.1, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "cutoff_high": ("FLOAT", {
                    "default": 0.4, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "order": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
            }
        }

    RETURN_TYPES = ("LINE",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = (
        "Frequency-domain filtering of a 1-D line profile. "
        "Supports lowpass, highpass, bandpass, and notch (band-reject) modes "
        "with a Butterworth roll-off. Cutoffs are fractions of the Nyquist frequency. "
        "Equivalent to Gwyddion fft_filter_1d."
    )

    def process(self, line, filter_type: str, cutoff: float,
                cutoff_high: float, order: int) -> tuple:
        z = np.asarray(line, dtype=np.float64).ravel()
        n = len(z)

        # Forward FFT (real-valued)
        Z = np.fft.rfft(z)

        # Build and apply transfer function
        H = _cached_1d_transfer(n, filter_type, float(cutoff), float(cutoff_high), int(order))
        Z *= H

        # Inverse FFT
        filtered = np.fft.irfft(Z, n=n)
        if isinstance(line, LineData):
            return (
                LineData(
                    data=filtered,
                    x_axis=line.x_axis.copy() if line.x_axis is not None else None,
                    x_unit=line.x_unit,
                    y_unit=line.y_unit,
                ),
            )
        return (filtered,)


# ---------------------------------------------------------------------------
# FFTFilter2D — frequency-domain filtering of DATA_FIELDs
# ---------------------------------------------------------------------------

@register_node(display_name="2D FFT Filter")
class FFTFilter2D:
    """Frequency-domain filtering of 2-D data fields (images).

    Equivalent to Gwyddion's fft_filter_2d module.  Applies a radial
    Butterworth transfer function in the frequency domain to remove or
    isolate periodic features.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "filter_type": (["lowpass", "highpass", "bandpass", "notch"],),
                "cutoff": ("FLOAT", {
                    "default": 0.1, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "cutoff_high": ("FLOAT", {
                    "default": 0.4, "min": 0.001, "max": 1.0, "step": 0.001,
                }),
                "order": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("filtered",)
    FUNCTION = "process"
    CATEGORY = "filters"
    DESCRIPTION = (
        "Frequency-domain filtering of a 2-D data field. "
        "Supports lowpass, highpass, bandpass, and notch (band-reject) modes "
        "with a radial Butterworth roll-off. Cutoffs are fractions of the "
        "Nyquist frequency. Use lowpass to smooth, highpass to sharpen, or "
        "bandpass/notch to isolate or remove periodic noise. "
        "Equivalent to Gwyddion fft_filter_2d."
    )

    def process(self, field: DataField, filter_type: str, cutoff: float,
                cutoff_high: float, order: int) -> tuple:
        data = field.data
        yres, xres = data.shape

        # Subtract mean to avoid DC leakage artefacts.
        mean_val = float(data.mean())
        centered = data - mean_val

        # Real-valued FFT keeps only the unique half-plane and avoids shift copies.
        spectrum = np.fft.rfft2(centered)
        transfer = _cached_2d_transfer(
            yres,
            xres,
            filter_type,
            float(cutoff),
            float(cutoff_high),
            int(order),
        )
        result = np.fft.irfft2(spectrum * transfer, s=(yres, xres))

        # Restore DC
        result += mean_val

        return (field.replace(data=result),)
