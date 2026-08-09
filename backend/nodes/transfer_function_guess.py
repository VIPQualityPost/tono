"""Transfer Function Guess — estimate the point-spread / transfer function from a
measured image and a known ideal response."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import correlate as ndi_correlate
from scipy.ndimage import distance_transform_edt, label

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table

def _fft2(a: np.ndarray) -> np.ndarray:
    return np.fft.fft2(np.asarray(a, dtype=np.float64))


def _ifft2_unnorm(F: np.ndarray) -> np.ndarray:
    """Inverse FFT without the 1/n normalisation, as FFTW's c2r transform."""
    n = F.shape[0] * F.shape[1]
    return np.fft.ifft2(F) * float(n)


def _humanize(a: np.ndarray) -> np.ndarray:
    """Humanized FFT: move zero frequency to the centre (odd-size
    convention keeps the DC block one item larger, same as fftshift)."""
    return np.fft.fftshift(a)


def _dehumanize(a: np.ndarray) -> np.ndarray:
    return np.fft.ifftshift(a)


def _window_vector(size: int, windowing: str) -> np.ndarray:
    """1-D window functions for the FFT preprocessing."""
    t = (np.arange(size, dtype=np.float64) + 0.5) / float(size)
    if windowing == "none":
        return np.ones(size, dtype=np.float64)
    if windowing == "hann":
        return 0.5 - 0.5 * np.cos(2.0 * np.pi * t)
    if windowing == "hamming":
        return 0.54 - 0.46 * np.cos(2.0 * np.pi * t)
    if windowing == "blackman":
        return 0.42 - 0.5 * np.cos(2.0 * np.pi * t) + 0.08 * np.cos(4.0 * np.pi * t)
    if windowing == "welch":
        x = 2.0 * (np.arange(size, dtype=np.float64) + 0.5) / float(size) - 1.0
        return 1.0 - x * x
    raise ValueError(f"Unknown windowing: {windowing!r}")


def _prepare_field(data: np.ndarray, windowing: str) -> np.ndarray:
    """Prepare the field for the FFT: subtract the mean and apply the window."""
    yres, xres = data.shape
    prepared = np.asarray(data, dtype=np.float64) - float(np.mean(data))
    if windowing != "none":
        wy = _window_vector(yres, windowing)
        wx = _window_vector(xres, windowing)
        prepared = prepared * np.outer(wy, wx)
    return prepared


# --- Unit handling for the transfer function (z_meas / z_ideal * xy^-2) ---

def _parse_unit(unit: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for token in str(unit or "").split():
        if not token:
            continue
        if token.startswith("1/"):
            base = token[2:].strip()
            counts[base] = counts.get(base, 0.0) - 1.0
        elif "^" in token:
            base, _, power = token.partition("^")
            counts[base] = counts.get(base, 0.0) + float(power)
        else:
            counts[token] = counts.get(token, 0.0) + 1.0
    return counts


def _format_unit(counts: dict[str, float]) -> str:
    parts: list[str] = []
    for base in sorted(counts):
        power = counts[base]
        if power == 0.0:
            continue
        if power == 1.0:
            parts.append(base)
        else:
            parts.append(f"{base}^{power:g}")
    return "\u00b7".join(parts)


def _combine_units(numerator: list[str], denominator: list[str]) -> str:
    merged: dict[str, float] = {}
    for unit in numerator:
        for base, power in _parse_unit(unit).items():
            merged[base] = merged.get(base, 0.0) + power
    for unit in denominator:
        for base, power in _parse_unit(unit).items():
            merged[base] = merged.get(base, 0.0) - power
    return _format_unit(merged)


# --- core deconvolution algorithms ---

def _deconvolve_regularized(meas: np.ndarray, ideal: np.ndarray, sigma: float,
                            dx: float, dy: float) -> np.ndarray:
    """Tikhonov regularisation."""
    yres, xres = meas.shape
    msq = float(np.mean(ideal * ideal))
    if not msq:
        raise ValueError("Ideal response has zero mean square — cannot deconvolve.")
    foper = _fft2(ideal)
    ffield = _fft2(meas)
    lam = sigma * msq * xres * yres
    numerator = ffield * np.conj(foper)
    denominator = np.abs(foper) ** 2 + lam
    fresult = numerator / denominator
    out = np.real(_ifft2_unnorm(fresult)) / (dx * dy * xres * yres)
    return _humanize(out)


def _deconvolve_wiener(meas: np.ndarray, ideal: np.ndarray, sigma: float,
                       dx: float, dy: float) -> np.ndarray:
    """Pseudo-Wiener filter with a sigma^2/|P|^2 term."""
    yres, xres = meas.shape
    orms = float(np.sqrt(np.mean(ideal * ideal)))
    frms = float(np.sqrt(np.mean(meas * meas)))
    if not orms or not frms:
        raise ValueError("Ideal or measured image is zero — cannot deconvolve.")
    # Compensate the unnormalised FFT.
    orms *= np.sqrt(xres * yres)
    frms *= np.sqrt(xres * yres)
    lam = sigma * sigma * orms * orms * frms * frms

    foper = _fft2(ideal)
    ffield = _fft2(meas)
    inorm = np.abs(foper) ** 2
    fnorm = np.abs(ffield) ** 2
    f = fnorm / (inorm * fnorm + lam)
    fresult = ffield * np.conj(foper) * f
    fresult[0, 0] = 0.0
    out = np.real(_ifft2_unnorm(fresult)) / (dx * dy * xres * yres)
    return _humanize(out)


def _copy_corners(source: np.ndarray, dest: np.ndarray, xlen: int, ylen: int) -> None:
    """Cut the central part of a dehumanised (dehumanized) field by copying the four
    corners of the array."""
    sy, sx = source.shape
    dy, dx = dest.shape
    dest[:] = 0.0
    dest[0:ylen, 0:xlen] = source[0:ylen, 0:xlen]
    dest[0:ylen, dx - (xlen - 1):] = source[0:ylen, sx - (xlen - 1):]
    dest[dy - (ylen - 1):, 0:xlen] = source[sy - (ylen - 1):, 0:xlen]
    dest[dy - (ylen - 1):, dx - (xlen - 1):] = source[sy - (ylen - 1):, sx - (xlen - 1):]


def _conjgrad_matrix_multiply(fmat: np.ndarray, vec: np.ndarray) -> np.ndarray:
    """FFT-based multiplication by the normal-equations matrix (symmetric, so only the
    real part of the spectrum is used)."""
    vy, vx = vec.shape
    xsize = fmat.shape[1]
    ysize = fmat.shape[0]
    buf = np.zeros((ysize, xsize), dtype=np.float64)
    _copy_corners(vec, buf, vx // 2 + 1, vy // 2 + 1)
    fvec = _fft2(buf)
    fvec *= np.real(fmat)
    outbuf = np.real(_ifft2_unnorm(fvec))
    result = np.zeros_like(vec)
    _copy_corners(outbuf, result, vx // 2 + 1, vy // 2 + 1)
    return result


def _deconvolve_psf_leastsq(meas: np.ndarray, ideal: np.ndarray,
                            txres: int, tyres: int, sigma: float, border: int,
                            dx: float, dy: float) -> np.ndarray:
    """Least-squares transfer function reconstruction solved with FFT-accelerated
    conjugate gradients."""
    yres, xres = meas.shape
    q = dx * dy
    txres |= 1  # force odd
    tyres |= 1
    xt = txres + 2 * border
    yt = tyres + 2 * border
    xsize = 2 * xt - 1
    ysize = 2 * yt - 1

    # Autocorrelation of the ideal image (left-hand-side matrix).
    fideal = _fft2(ideal)
    autocor = np.real(_ifft2_unnorm(np.abs(fideal) ** 2)) / float(xres * yres)

    # Cross-correlation ideal * measured (right-hand side).
    fmeas = _fft2(meas)
    product = np.real(_ifft2_unnorm(fmeas * np.conj(fideal))) / float(xres * yres)

    matrix = np.zeros((ysize, xsize), dtype=np.float64)
    _copy_corners(autocor, matrix, xt, yt)
    rhs = np.zeros((yt, xt), dtype=np.float64)
    _copy_corners(product, rhs, xt // 2 + 1, yt // 2 + 1)

    # Scale matrix and rhs in sync, as in conjgrad_make_equations().
    fnorm = float(np.sqrt(np.mean(rhs * rhs)))
    if fnorm > 0.0:
        scale = 1e24 / fnorm
        rhs *= scale
        matrix *= scale
    else:
        fnorm = 1.0

    # Normalise sigma relatively to the data.
    mnorm = float(np.mean(ideal * ideal))
    mnorm *= xres * yres
    mnorm *= np.cbrt(float(txres * tyres))
    lam = sigma * mnorm * fnorm
    matrix[0, 0] += lam

    fmat = _fft2(matrix / float(xsize * ysize))

    # Conjugate gradient solve (maxiter 150, eps 1e-40).
    tf = np.zeros((yt, xt), dtype=np.float64)
    vfield = _conjgrad_matrix_multiply(fmat, tf) - rhs
    ffield = vfield.copy()
    wfield = _conjgrad_matrix_multiply(fmat, vfield)
    fnorm0 = float(np.mean(ffield * ffield))
    for _ in range(150):
        numer = float(np.sum(ffield * vfield))
        denom = float(np.sum(vfield * wfield))
        if numer == 0.0 or denom == 0.0:
            break
        qstep = numer / denom
        tf -= qstep * vfield
        ffield -= qstep * wfield
        if float(np.mean(ffield * ffield)) <= 1e-40 * fnorm0:
            break
        vfield = ffield - (float(np.sum(ffield * wfield)) / denom) * vfield
        wfield = _conjgrad_matrix_multiply(fmat, vfield)

    tf = _humanize(tf)
    if border > 0:
        tf = tf[border:border + tyres, border:border + txres]
    return tf / q


# --- sigma estimation / measurement helpers ---

def _golden_section_min(func, a: float, b: float) -> float:
    """1-D golden-section minimisation over [a, b] on a unimodal function."""
    gr = (np.sqrt(5.0) - 1.0) / 2.0
    c = b - gr * (b - a)
    d = a + gr * (b - a)
    fc, fd = func(c), func(d)
    while (b - a) > 1e-12 * (abs(a) + abs(b)):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - gr * (b - a)
            fc = func(c)
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b - a)
            fd = func(d)
    return 0.5 * (a + b)


def _region_dispersion(data: np.ndarray) -> float:
    """sqrt of the dispersion (variance) over the central xres/3..2/3 region."""
    yres, xres = data.shape
    col = xres // 3
    row = yres // 3
    region = data[row:row + yres - 2 * row, col:col + xres - 2 * col]
    return float(np.sqrt(np.var(np.abs(region))))


def _find_regularization_sigma(meas: np.ndarray, ideal: np.ndarray, method: str,
                               dx: float, dy: float) -> float:
    """Find the regularisation sigma for the regularised and Wiener branches.
    Returns the linear sigma."""
    yres, xres = meas.shape
    foper = _fft2(ideal)
    fmeas = _fft2(meas)

    if method == "regularised":
        msq = float(np.mean(ideal * ideal))
        sigma_scale = msq * xres * yres

        def resid(logsigma: float) -> float:
            sigma = np.exp(logsigma)
            lam = sigma * sigma_scale
            fpsf = (fmeas * np.conj(foper)) / (np.abs(foper) ** 2 + lam)
            psf = _humanize(np.real(_ifft2_unnorm(fpsf)) / (dx * dy * xres * yres))
            return _region_dispersion(psf)

        logbest = _golden_section_min(resid, np.log(1e-8), np.log(1e3))
        # Experimentally determined fudge factor from large-scale simulations.
        return 0.276 * float(np.exp(logbest))

    orms = float(np.sqrt(np.mean(ideal * ideal))) * np.sqrt(xres * yres)
    frms = float(np.sqrt(np.mean(meas * meas))) * np.sqrt(xres * yres)

    def resid(logsigma: float) -> float:
        sigma = np.exp(logsigma)
        lam = sigma * sigma * orms * orms * frms * frms
        inorm = np.abs(foper) ** 2
        fnorm = np.abs(fmeas) ** 2
        f = fnorm / (inorm * fnorm + lam)
        fresult = fmeas * np.conj(foper) * f
        fresult[0, 0] = 0.0
        psf = _humanize(np.real(_ifft2_unnorm(fresult)) / (dx * dy * xres * yres))
        return _region_dispersion(psf)

    logbest = _golden_section_min(resid, np.log(1e-8), np.log(1e3))
    # Experimentally determined fudge factor from large-scale simulations.
    return 0.375 * float(np.exp(logbest))


def _ext_convolve(field: np.ndarray, kernel: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Extend-convolve with border-extended exterior and as_integral=TRUE:
    nearest-neighbour (edge-extended) correlation scaled by dx*dy."""
    return ndi_correlate(field, kernel, mode="nearest") * (dx * dy)


def _measure_tf_width(psf: np.ndarray) -> float:
    """Measure the transfer function width: threshold the PSF, keep the central grain,
    grow it by 0.5*log(xres*yres) and report the dispersion of |PSF| inside."""
    yres, xres = psf.shape
    thresh = 0.15 * float(np.max(psf))
    mask = np.asarray(psf > thresh, dtype=np.uint8)
    if mask[yres // 2, xres // 2] == 0:
        return 0.0
    labels, _ = label(mask)
    central = labels[yres // 2, xres // 2]
    centre_grain = labels == central
    radius = 0.5 * np.log(float(xres * yres))
    dist = distance_transform_edt(~centre_grain)
    grown = dist <= radius
    abspsf = np.abs(psf)
    return float(np.sqrt(np.var(abspsf[grown])))


def _l2_norm(data: np.ndarray, dx: float, dy: float, as_integral: bool) -> float:
    """Integral or discrete L2 norm."""
    yres, xres = data.shape
    if as_integral:
        q = dx * xres * dy * yres
    else:
        q = float(xres * yres)
    return float(np.sqrt(q * np.mean(data * data)))


@register_node(display_name="Transfer Function Guess")
class TransferFunctionGuess:
    CATEGORY = "Spectral"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "ideal": ("DATA_FIELD",),
                "method": (["regularised", "wiener", "least_squares"], {"default": "regularised"}),
                "sigma_log10": ("FLOAT", {"default": 1.0, "min": -8.0, "max": 3.0, "step": 0.05}),
                "auto_sigma": ("BOOLEAN", {"default": False}),
                "txres": ("INT", {"default": 51, "min": 3, "max": 16384, "step": 2}),
                "tyres": ("INT", {"default": 51, "min": 3, "max": 16384, "step": 2}),
                "border": ("INT", {"default": 3, "min": 0, "max": 512, "step": 1}),
                "windowing": (["welch", "none", "hann", "hamming", "blackman"], {"default": "welch"}),
                "as_integral": ("BOOLEAN", {"default": True}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'psf'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Estimate the point spread / transfer function of an imaging system from a "
        "measured image and a known ideal response. "
        "Three deconvolution methods are available: regularised filter (default), "
        "pseudo-Wiener filter and least squares on a small transfer-function support. "
        "The measurement table reports the transfer function width and norms, and the "
        "regularization sigma used."
    )

    KEYWORDS = ("transfer function", "psf", "deconvolution", "point spread function", "wiener")

    def process(self, field: DataField, ideal: DataField, method: str, sigma_log10: float,
                auto_sigma: bool, txres: int, tyres: int, border: int, windowing: str,
                as_integral: bool) -> tuple:
        if not isinstance(ideal, DataField) or ideal.data is None:
            raise ValueError("An ideal response field must be connected.")
        if (ideal.xres != field.xres or ideal.yres != field.yres
                or not np.isclose(ideal.xreal, field.xreal) or not np.isclose(ideal.yreal, field.yreal)):
            raise ValueError("Ideal response must have the same resolution and physical size as the measured field.")
        if min(field.xres, field.yres) < 24:
            raise ValueError("Image is too small; transfer function estimation needs at least 24 pixels.")

        xres, yres = field.xres, field.yres
        dx = field.dx if field.xres else 1.0
        dy = field.dy if field.yres else 1.0
        meas = _prepare_field(np.asarray(field.data, dtype=np.float64), windowing)
        ideal_arr = _prepare_field(np.asarray(ideal.data, dtype=np.float64), windowing)

        txres = max(3, min(int(txres), xres))
        tyres = max(3, min(int(tyres), yres))

        if auto_sigma and method != "least_squares":
            sigma = _find_regularization_sigma(meas, ideal_arr, method, dx, dy)
        else:
            sigma = 10.0 ** sigma_log10

        yoff_out = field.yoff
        xoff_out = field.xoff
        if method == "regularised":
            psf = _deconvolve_regularized(meas, ideal_arr, sigma, dx, dy)
            crop = (txres < xres) or (tyres < yres)
        elif method == "wiener":
            psf = _deconvolve_wiener(meas, ideal_arr, sigma, dx, dy)
            crop = (txres < xres) or (tyres < yres)
        elif method == "least_squares":
            psf = _deconvolve_psf_leastsq(meas, ideal_arr, txres, tyres, sigma, border, dx, dy)
            crop = False
            # The least-squares TF is centered on its own support.
            yoff_out = -0.5 * tyres * dy
            xoff_out = -0.5 * txres * dx
        else:
            raise ValueError(f"Unknown method: {method!r}")

        if crop:
            yres_full, xres_full = psf.shape
            xborder = (xres_full - txres + 1) // 2
            yborder = (yres_full - tyres + 1) // 2
            if xborder or yborder:
                psf = psf[yborder:yborder + tyres, xborder:xborder + txres]
                xoff_out = field.xoff + xborder * dx
                yoff_out = field.yoff + yborder * dy

        if not as_integral:
            psf = psf * (dx * dy)

        # --- measurement table ---
        z_meas = field.si_unit_z
        z_ideal = ideal.si_unit_z
        xy = field.si_unit_xy
        tf_z_unit = _combine_units([z_meas], [z_ideal, xy, xy])
        if not as_integral:
            tf_z_unit = _combine_units([tf_z_unit, xy, xy], [])

        width = _measure_tf_width(psf)
        height = float(max(abs(psf.min()), abs(psf.max())))

        yres_out, xres_out = psf.shape
        # Integral norm units: product of PSF lateral and value units; discrete
        # norm keeps only the value unit.
        norm_unit = _combine_units([xy, tf_z_unit], []) if as_integral else tf_z_unit
        l2norm = _l2_norm(psf, dx, dy, as_integral)

        convolved = _ext_convolve(np.asarray(ideal.data, dtype=np.float64)
                                  - float(np.mean(ideal.data)), psf, dx, dy)
        convolved = convolved + float(np.mean(field.data))
        difference = np.asarray(field.data, dtype=np.float64) - convolved
        residuum = _l2_norm(difference, dx, dy, as_integral)

        rows = [
            {"quantity": "TF width", "value": float(width), "unit": xy},
            {"quantity": "TF height", "value": float(height), "unit": tf_z_unit},
            {"quantity": "TF norm", "value": float(l2norm), "unit": norm_unit},
            {"quantity": "Difference norm", "value": float(residuum), "unit": norm_unit},
            {"quantity": "Regularization sigma", "value": float(sigma), "unit": ""},
        ]
        measurement = RecordTable(rows)
        emit_table(measurement)

        psf_field = DataField(
            data=psf,
            xreal=float(xres_out * dx),
            yreal=float(yres_out * dy),
            xoff=float(xoff_out),
            yoff=float(yoff_out),
            si_unit_xy=xy,
            si_unit_z=tf_z_unit,
            domain="spatial",
            colormap=field.colormap,
        )
        return (psf_field, measurement)
