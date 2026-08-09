"""MFM Parallel Media — stray field above in-plane magnetised stripe media."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField

# Vacuum permeability (exact constant used by Gwyddion's libprocess/mfm.c), N/A^2.
MU_0 = 1.256637061435917295e-6

_OPERATIONS = ("hx", "hz", "force", "force_dz", "force_ddz")
_PROBES = ("point_charge", "bar")


def _gwy_sinc(x):
    """Unnormalised cardinal sine used by Gwyddion: sin(x)/x, with 1 - x^2/6 near 0."""
    x = np.asarray(x, dtype=np.float64)
    out = np.empty_like(x)
    big = np.abs(x) > 3e-4
    out[big] = np.sin(x[big]) / x[big]
    out[~big] = 1.0 - x[~big] * x[~big] / 6.0
    return out


def _parallel_medium_row(xres, xreal, height, size_a, size_b, size_c,
                         magnetisation, thickness, component):
    """Port of gwy_data_field_mfm_parallel_medium (libprocess/mfm.c): one row of the
    stray field above a medium of alternating left/right magnetised stripes.

    The C accumulates boundary contributions from 'oriented area walls': each
    stripe boundary at xlist[k] with direction dirlist[k] contributes an
    analytic wall-field term (Biot-Savart style closed forms).  The medium is
    extended d = 20*(a + b + t + h) beyond the field on both sides so the
    result is the field of a quasi-infinite periodic medium.
    """
    m = MU_0 * magnetisation / np.pi
    d = 20.0 * (size_a + size_b + thickness + height)
    pos = -d

    # Boundary list: stripes of width a (dir +1) and b (dir -1) separated by gaps c.
    xlist = [pos * xres / xreal]
    dirlist = [1]
    while True:
        pos += size_a + size_c / 2.0
        xlist.append(pos * xres / xreal)
        dirlist.append(-1)
        pos += size_b + size_c / 2.0
        xlist.append(pos * xres / xreal)
        dirlist.append(1)
        if pos >= xreal + d or len(xlist) >= 10 * xres:
            break

    j = np.arange(xres, dtype=np.float64)
    row = np.zeros(xres, dtype=np.float64)
    c = size_c
    for xk, dir_k in zip(xlist, dirlist):
        x = (j - xk) * xreal / xres
        if component == "hx":
            u = x * x + c * c + c * (thickness + height)
            v = x * x + c * c + c * height
            row += -m * dir_k * (np.arctan(x * (thickness + height) / u)
                                 - np.arctan(x * height / v))
        elif component == "hy":
            pass  # in-plane parallel media have no y component
        elif component == "hz":
            u = c + height + thickness
            v = c + height
            row += 0.5 * m * dir_k * np.log((x * x + u * u) / (x * x + v * v))
        elif component == "dhz_dz":
            u = c + height + thickness
            v = c + height
            row += m * dir_k * (u / (x * x + u * u) - v / (x * x + v * v))
        elif component == "d2hz_dz2":
            u = c + height + thickness
            v = c + height
            row += m * dir_k * ((x * x - u * u) / (x * x + u * u)
                                - (x * x - v * v) / (x * x + v * v))
        else:
            raise ValueError(f"Unknown MFM component: {component!r}")
    return row


def _mfm_perpendicular_force(hz_2d, xreal, yreal, probe, mtip, bx, by, length):
    """Port of gwy_data_field_mfm_perpendicular_medium_force + the static
    mfm_perpendicular_create_ftf (libprocess/mfm.c): force on a point-charge or
    bar probe from the z-component of the stray field, via FFT multiplication
    with the probe transfer function.

    Fz = ifft(fft(hz) * ftf)  with
    ftf = -mu0*mtip*bx*by * sinc(kx*bx/2) * sinc(ky*by/2) * (1 - exp(-|k|*length))
    (ftf constant for the point-charge probe, i.e. Fz = c*Hz).
    """
    yres, xres = hz_2d.shape
    c = -MU_0 * mtip * bx * by
    if probe == "point_charge":
        ftf = np.full((yres, xres), c, dtype=np.float64)
    elif probe == "bar":
        kx = np.fft.fftfreq(xres, d=xreal / xres)   # cycles per metre
        ky = np.fft.fftfreq(yres, d=yreal / yres)
        KX, KY = np.meshgrid(kx, ky)
        K = np.sqrt(KX * KX + KY * KY)
        ftf = (c * _gwy_sinc(KX * bx / 2.0) * _gwy_sinc(KY * by / 2.0)
               * (1.0 - np.exp(-K * length)))
    else:
        raise ValueError(f"Unknown probe type: {probe!r}")
    return np.real(np.fft.ifft2(np.fft.fft2(hz_2d) * ftf))


@register_node(display_name="MFM Parallel Media")
class MFMParallelMedia:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "operation": (list(_OPERATIONS), {"default": "hz"}),
                "probe": (list(_PROBES), {"default": "point_charge"}),
                "height": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "thickness": ("FLOAT", {
                    "default": 100e-9, "min": 0.0, "max": 1e-6, "step": 1e-9,
                }),
                "magnetization": ("FLOAT", {
                    "default": 1e6, "min": 1.0, "max": 1e8, "step": 1.0,
                }),
                "size_a": ("FLOAT", {
                    "default": 200e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
                "size_b": ("FLOAT", {
                    "default": 200e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
                "size_c": ("FLOAT", {
                    "default": 10e-9, "min": 0.0, "max": 10e-6, "step": 1e-9,
                }),
                "mtip": ("FLOAT", {
                    "default": 1e3, "min": 1.0, "max": 1e8, "step": 1.0,
                }),
                "bx": ("FLOAT", {
                    "default": 10e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "by": ("FLOAT", {
                    "default": 10e-9, "min": 1e-9, "max": 10e-6, "step": 1e-9,
                }),
                "length": ("FLOAT", {
                    "default": 500e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
    )
    FUNCTION = "process"

    CATEGORY = "Detect"

    DESCRIPTION = (
        "Simulates the stray field above an in-plane magnetised parallel medium: "
        "alternating stripes with left/right remanent magnetisation, separated by "
        "gaps. Ports Gwyddion's mfm_parallel module (gwy_data_field_mfm_parallel_medium) "
        "with its closed-form Biot-Savart wall contributions and optional probe "
        "force calculation (point charge or bar). The field parameter only "
        "provides the lateral grid template; its values are ignored."
    )

    KEYWORDS = ("magnetic", "mfM", "parallel media", "stray field", "stripe", "simulation", "biot savart")

    def process(
        self,
        field: DataField,
        operation: str,
        probe: str,
        height: float,
        thickness: float,
        magnetization: float,
        size_a: float,
        size_b: float,
        size_c: float,
        mtip: float,
        bx: float,
        by: float,
        length: float,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape

        if operation == "hx":
            component, z_unit = "hx", "A/m"
        elif operation == "hz":
            component, z_unit = "hz", "A/m"
        elif operation == "force":
            component, z_unit = "hz", "N"
        elif operation == "force_dz":
            component, z_unit = "dhz_dz", "N/m"
        elif operation == "force_ddz":
            component, z_unit = "d2hz_dz2", "N/m²"
        else:
            raise ValueError(f"Unknown output type: {operation!r}")

        row = _parallel_medium_row(xres, field.xreal, height, size_a, size_b,
                                   size_c, magnetization, thickness, component)
        grid = np.tile(row, (yres, 1))

        if operation in ("force", "force_dz", "force_ddz"):
            grid = _mfm_perpendicular_force(grid, field.xreal, field.yreal,
                                            probe, mtip, bx, by, length)

        return (field.replace(data=grid, si_unit_z=z_unit),)
