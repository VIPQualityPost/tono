"""PSF estimation — estimate and fit point spread functions for deconvolution."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="PSF Estimation")
class PSFEstimation:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "measured": ("DATA_FIELD",),
                "ideal": ("DATA_FIELD",),
                "method": (["wiener", "least_squares", "gaussian_fit"], {"default": "wiener"}),
                "regularization": ("FLOAT", {"default": 0.01, "min": 1e-6, "max": 1.0, "step": 0.001}),
                "psf_size": ("INT", {"default": 32, "min": 4, "max": 128}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'psf'),
        ('RECORD_TABLE', 'parameters'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Estimate a point spread function (PSF) from a measured (blurred) image "
        "and an ideal (sharp) reference. The PSF can then be used with the "
        "Deconvolution node to restore other images. Three methods are available: "
        "pseudo-Wiener deconvolution, regularised least-squares, and Gaussian fit. "
        "All methods report fitted Gaussian parameters (sigma_x, sigma_y, amplitude). "
    )

    KEYWORDS = ("point spread function", "deconvolution", "wiener", "gaussian", "blur", "kernel")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _crop_centre(arr: np.ndarray, size: int) -> np.ndarray:
        """Crop the central *size x size* region from *arr*."""
        yc, xc = arr.shape[0] // 2, arr.shape[1] // 2
        half = size // 2
        return arr[yc - half : yc - half + size, xc - half : xc - half + size]

    @staticmethod
    def _normalise(psf: np.ndarray) -> np.ndarray:
        """Normalise so that the PSF sums to 1."""
        s = psf.sum()
        if abs(s) > 1e-30:
            psf = psf / s
        return psf

    @staticmethod
    def _fit_gaussian_2d(psf: np.ndarray):
        """Fit a 2-D Gaussian to *psf* using moment analysis.

        Returns (gaussian_array, sigma_x, sigma_y, amplitude).
        """
        h, w = psf.shape
        psf_pos = np.maximum(psf, 0.0)
        total = psf_pos.sum()
        if total < 1e-30:
            return np.zeros_like(psf), 0.0, 0.0, 0.0

        y_idx, x_idx = np.mgrid[0:h, 0:w]

        # centroid
        cx = float(np.sum(x_idx * psf_pos) / total)
        cy = float(np.sum(y_idx * psf_pos) / total)

        # second moments → sigma
        sx = float(np.sqrt(np.sum(psf_pos * (x_idx - cx) ** 2) / total))
        sy = float(np.sqrt(np.sum(psf_pos * (y_idx - cy) ** 2) / total))
        sx = max(sx, 1e-6)
        sy = max(sy, 1e-6)

        amplitude = float(psf_pos.max())

        gauss = amplitude * np.exp(
            -((x_idx - cx) ** 2 / (2 * sx ** 2) + (y_idx - cy) ** 2 / (2 * sy ** 2))
        )
        gauss = PSFEstimation._normalise(gauss)
        return gauss, sx, sy, amplitude

    # ------------------------------------------------------------------
    # methods
    # ------------------------------------------------------------------

    def _wiener(
        self,
        F_measured: np.ndarray,
        F_ideal: np.ndarray,
        regularization: float,
        psf_size: int,
    ) -> np.ndarray:
        """Pseudo-Wiener PSF estimation."""
        F_psf = np.conj(F_ideal) * F_measured / (np.abs(F_ideal) ** 2 + regularization)
        psf = np.real(np.fft.ifft2(F_psf))
        psf = np.fft.fftshift(psf)
        psf = self._crop_centre(psf, psf_size)
        return self._normalise(psf)

    def _least_squares(
        self,
        F_measured: np.ndarray,
        F_ideal: np.ndarray,
        regularization: float,
        psf_size: int,
    ) -> np.ndarray:
        """Regularised least-squares PSF estimation."""
        abs_ideal = np.abs(F_ideal)
        F_psf = np.where(
            abs_ideal < regularization,
            0.0,
            F_measured / (F_ideal + regularization * np.sign(F_ideal)),
        )
        psf = np.real(np.fft.ifft2(F_psf))
        psf = np.fft.fftshift(psf)
        psf = self._crop_centre(psf, psf_size)
        return self._normalise(psf)

    # ------------------------------------------------------------------
    # main entry
    # ------------------------------------------------------------------

    def process(
        self,
        measured: DataField,
        ideal: DataField,
        method: str,
        regularization: float,
        psf_size: int,
    ) -> tuple:
        measured_data = np.asarray(measured.data, dtype=np.float64)
        ideal_data = np.asarray(ideal.data, dtype=np.float64)

        F_measured = np.fft.fft2(measured_data)
        F_ideal = np.fft.fft2(ideal_data)

        parameters = RecordTable()

        if method == "wiener":
            psf = self._wiener(F_measured, F_ideal, regularization, psf_size)
            _, sigma_x, sigma_y, amplitude = self._fit_gaussian_2d(psf)
            parameters = RecordTable([
                {"quantity": "sigma_x",   "value": sigma_x,   "unit": "px"},
                {"quantity": "sigma_y",   "value": sigma_y,   "unit": "px"},
                {"quantity": "amplitude", "value": amplitude,  "unit": ""},
            ])

        elif method == "least_squares":
            psf = self._least_squares(F_measured, F_ideal, regularization, psf_size)
            _, sigma_x, sigma_y, amplitude = self._fit_gaussian_2d(psf)
            parameters = RecordTable([
                {"quantity": "sigma_x",   "value": sigma_x,   "unit": "px"},
                {"quantity": "sigma_y",   "value": sigma_y,   "unit": "px"},
                {"quantity": "amplitude", "value": amplitude,  "unit": ""},
            ])

        elif method == "gaussian_fit":
            raw_psf = self._wiener(F_measured, F_ideal, regularization, psf_size)
            psf, sigma_x, sigma_y, amplitude = self._fit_gaussian_2d(raw_psf)
            parameters = RecordTable([
                {"quantity": "sigma_x",   "value": sigma_x,   "unit": "px"},
                {"quantity": "sigma_y",   "value": sigma_y,   "unit": "px"},
                {"quantity": "amplitude", "value": amplitude,  "unit": ""},
            ])
        else:
            raise ValueError(f"Unknown PSF estimation method: {method!r}")

        # Build output DataField — inherit spatial metadata, adjust for psf_size
        yres, xres = measured_data.shape
        psf_xreal = measured.xreal * psf_size / xres
        psf_yreal = measured.yreal * psf_size / yres

        psf_field = measured.replace(
            data=psf,
            xreal=psf_xreal,
            yreal=psf_yreal,
            xoff=0.0,
            yoff=0.0,
        )

        emit_table(parameters)

        return (psf_field, parameters)
