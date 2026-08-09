"""DWT anisotropy — quantify surface anisotropy using wavelet decomposition."""

from __future__ import annotations

import numpy as np

from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table
from backend.node_registry import register_node


def _next_power_of_2(n: int) -> int:
    """Return the smallest power of 2 >= n."""
    p = 1
    while p < n:
        p <<= 1
    return p


def _pad_to_pow2(data: np.ndarray) -> np.ndarray:
    """Pad *data* to the next power-of-2 dimensions using edge values."""
    rows, cols = data.shape
    new_rows = _next_power_of_2(rows)
    new_cols = _next_power_of_2(cols)
    if new_rows == rows and new_cols == cols:
        return data.copy()
    out = np.zeros((new_rows, new_cols), dtype=np.float64)
    out[:rows, :cols] = data
    # edge-pad
    if new_cols > cols:
        out[:rows, cols:] = data[:, -1:]
    if new_rows > rows:
        out[rows:, :cols] = data[-1:, :]
    if new_rows > rows and new_cols > cols:
        out[rows:, cols:] = data[-1, -1]
    return out


def _haar_decompose_2d(data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    One level of 2-D Haar wavelet decomposition.

    Returns (LL, LH, HL, HH) each of shape (rows//2, cols//2).
    LL = (a+b+c+d)/2   approximation
    LH = (a+b-c-d)/2   horizontal detail  (captures vertical features)
    HL = (a-b+c-d)/2   vertical detail    (captures horizontal features)
    HH = (a-b-c+d)/2   diagonal detail
    """
    rows, cols = data.shape
    a = data[0::2, 0::2]  # top-left
    b = data[0::2, 1::2]  # top-right
    c = data[1::2, 0::2]  # bottom-left
    d = data[1::2, 1::2]  # bottom-right

    ll = (a + b + c + d) / 2.0
    lh = (a + b - c - d) / 2.0
    hl = (a - b + c - d) / 2.0
    hh = (a - b - c + d) / 2.0
    return ll, lh, hl, hh


def _compute_dwt_anisotropy(
    data: np.ndarray,
    n_levels: int,
) -> tuple[list[float], list[float], list[float], list[np.ndarray]]:
    """
    Multi-level 2-D Haar decomposition with per-level energy ratios.

    Returns
    -------
    x_energies : per-level sum(HL**2)
    y_energies : per-level sum(LH**2)
    ratios     : per-level x_energy / y_energy
    ratio_maps : per-level ratio arrays (at decomposition resolution)
    """
    padded = _pad_to_pow2(np.asarray(data, dtype=np.float64))
    current = padded

    x_energies: list[float] = []
    y_energies: list[float] = []
    ratios: list[float] = []
    ratio_maps: list[np.ndarray] = []

    for _ in range(n_levels):
        if current.shape[0] < 2 or current.shape[1] < 2:
            break
        ll, lh, hl, hh = _haar_decompose_2d(current)

        x_energy = float(np.sum(hl ** 2))
        y_energy = float(np.sum(lh ** 2))
        ratio = x_energy / (y_energy + 1e-30)

        x_energies.append(x_energy)
        y_energies.append(y_energy)
        ratios.append(ratio)

        # Build a per-pixel ratio map at this level's resolution
        hl_sq = hl ** 2
        lh_sq = lh ** 2
        level_map = hl_sq / (lh_sq + 1e-30)
        ratio_maps.append(level_map)

        current = ll

    return x_energies, y_energies, ratios, ratio_maps


def _build_anisotropy_map(
    ratio_maps: list[np.ndarray],
    orig_rows: int,
    orig_cols: int,
) -> np.ndarray:
    """
    Combine per-level ratio maps into a single anisotropy map at
    the original field resolution by upsampling and averaging.
    """
    if not ratio_maps:
        return np.ones((orig_rows, orig_cols), dtype=np.float64)

    from scipy.ndimage import zoom

    target = np.zeros((orig_rows, orig_cols), dtype=np.float64)
    for level_map in ratio_maps:
        zy = orig_rows / level_map.shape[0]
        zx = orig_cols / level_map.shape[1]
        upsampled = zoom(level_map, (zy, zx), order=1)
        # zoom may produce shape off by one — trim or pad
        upsampled = upsampled[:orig_rows, :orig_cols]
        if upsampled.shape[0] < orig_rows or upsampled.shape[1] < orig_cols:
            tmp = np.ones((orig_rows, orig_cols), dtype=np.float64)
            tmp[: upsampled.shape[0], : upsampled.shape[1]] = upsampled
            upsampled = tmp
        target += upsampled

    target /= len(ratio_maps)
    return target


@register_node(display_name="DWT Anisotropy")
class DWTAnisotropy:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_levels": (
                    "INT",
                    {"default": 4, "min": 1, "max": 10},
                ),
                "ratio_threshold": (
                    "FLOAT",
                    {"default": 0.2, "min": 0.001, "max": 10.0, "step": 0.01},
                ),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'anisotropy_map'),
        ('RECORD_TABLE', 'statistics'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Quantify surface anisotropy using a multi-level 2-D Haar wavelet decomposition. "
        "At each level, horizontal (HL) and vertical (LH) detail energies are compared to "
        "produce an X/Y energy ratio. Ratio > 1 indicates more horizontal features; "
        "ratio < 1 indicates more vertical features."
    )

    KEYWORDS = ("wavelet", "haar", "directional", "texture")

    def process(
        self,
        field: DataField,
        n_levels: int,
        ratio_threshold: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        orig_rows, orig_cols = data.shape

        x_energies, y_energies, ratios, ratio_maps = _compute_dwt_anisotropy(
            data, int(n_levels),
        )

        # Build per-pixel anisotropy map
        aniso_map = _build_anisotropy_map(ratio_maps, orig_rows, orig_cols)
        aniso_field = field.replace(data=aniso_map)

        # Build statistics table
        rows = []
        for i, (xe, ye, r) in enumerate(zip(x_energies, y_energies, ratios)):
            rows.append({
                "quantity": f"Level {i + 1} X energy",
                "value": float(xe),
                "unit": "",
            })
            rows.append({
                "quantity": f"Level {i + 1} Y energy",
                "value": float(ye),
                "unit": "",
            })
            rows.append({
                "quantity": f"Level {i + 1} X/Y ratio",
                "value": float(r),
                "unit": "",
            })
            rows.append({
                "quantity": f"Level {i + 1} anisotropic",
                "value": 1.0 if abs(r - 1.0) > float(ratio_threshold) else 0.0,
                "unit": "",
            })
        stats = RecordTable(rows)

        emit_table(stats)

        return (aniso_field, stats)
