"""Lattice measurement — detect and measure periodic lattice structures."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


def _find_acf_peaks(acf: np.ndarray, dx: float, dy: float, n_peaks: int = 6):
    """Find the strongest off-centre peaks in a 2D ACF.

    Returns list of (row, col, distance, angle_deg) tuples sorted by
    correlation strength.
    """
    yres, xres = acf.shape
    cy, cx = yres // 2, xres // 2

    # Mask the central DC region (within ~5% of the field size)
    mask_radius = max(3, min(yres, xres) // 20)
    yy, xx = np.ogrid[:yres, :xres]
    dc_mask = ((yy - cy) ** 2 + (xx - cx) ** 2) <= mask_radius ** 2
    acf_masked = acf.copy()
    acf_masked[dc_mask] = -np.inf

    peaks = []
    for _ in range(n_peaks):
        idx = np.argmax(acf_masked)
        r, c = np.unravel_index(idx, acf.shape)
        if acf_masked[r, c] == -np.inf:
            break
        # Physical distance from centre
        dist_x = (c - cx) * dx
        dist_y = (r - cy) * dy
        distance = np.hypot(dist_x, dist_y)
        angle = np.degrees(np.arctan2(dist_y, dist_x))
        peaks.append((r, c, distance, angle, float(acf[r, c])))
        # Suppress neighbourhood
        sup_r = max(0, r - mask_radius), min(yres, r + mask_radius + 1)
        sup_c = max(0, c - mask_radius), min(xres, c + mask_radius + 1)
        acf_masked[sup_r[0]:sup_r[1], sup_c[0]:sup_c[1]] = -np.inf

    return peaks


@register_node(display_name="Lattice Measurement")
class LatticeMeasurement:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "method": (["acf", "fft"], {"default": "acf"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'correlation'),
        ('RECORD_TABLE', 'lattice'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect and measure periodic lattice structures from a surface. "
        "Computes the 2D ACF or FFT power spectrum, finds the strongest peaks, "
        "and reports lattice vectors (spacing and angle). "
    )

    def process(self, field: DataField, method: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        data = data - data.mean()

        if method == "acf":
            fft_data = np.fft.fft2(data)
            power = np.abs(fft_data) ** 2
            acf = np.real(np.fft.ifft2(power))
            acf = np.fft.fftshift(acf)
            acf /= acf.max() if acf.max() != 0 else 1.0
            corr_field = field.replace(data=acf, si_unit_z="", domain="spatial")
        elif method == "fft":
            fft_data = np.fft.fft2(data)
            power = np.fft.fftshift(np.abs(fft_data) ** 2)
            power = np.log1p(power)
            corr_field = field.replace(data=power, si_unit_z="", domain="frequency")
        else:
            raise ValueError(f"Unknown method: {method!r}")

        # Find lattice peaks from ACF
        if method == "fft":
            # Convert FFT peaks to ACF for lattice measurement
            fft_data = np.fft.fft2(data)
            power_raw = np.abs(fft_data) ** 2
            acf = np.real(np.fft.ifft2(power_raw))
            acf = np.fft.fftshift(acf)
            acf /= acf.max() if acf.max() != 0 else 1.0

        peaks = _find_acf_peaks(acf, field.dx, field.dy)

        records: RecordTable = RecordTable()
        if len(peaks) >= 1:
            _, _, d1, a1, s1 = peaks[0]
            records.append({"quantity": "Vector 1 spacing", "value": f"{d1:.4g}", "unit": field.si_unit_xy})
            records.append({"quantity": "Vector 1 angle", "value": f"{a1:.1f}", "unit": "deg"})
            records.append({"quantity": "Vector 1 strength", "value": f"{s1:.4g}", "unit": ""})
        if len(peaks) >= 2:
            _, _, d2, a2, s2 = peaks[1]
            records.append({"quantity": "Vector 2 spacing", "value": f"{d2:.4g}", "unit": field.si_unit_xy})
            records.append({"quantity": "Vector 2 angle", "value": f"{a2:.1f}", "unit": "deg"})
            records.append({"quantity": "Vector 2 strength", "value": f"{s2:.4g}", "unit": ""})
        if len(peaks) >= 2:
            angle_diff = abs(peaks[1][3] - peaks[0][3])
            records.append({"quantity": "Lattice angle", "value": f"{angle_diff:.1f}", "unit": "deg"})

        return (corr_field, records)
