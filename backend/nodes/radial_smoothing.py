"""Radial smoothing — smooth images in polar coordinates."""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates

from backend.data_types import DataField
from backend.node_registry import register_node

_INTERP_ORDER = {"linear": 1, "cubic": 3, "nearest": 0}


def _polar_dimensions(xres: int, yres: int) -> tuple[int, int]:
    """Polar sampling field dimensions: (radius resolution, angular resolution)."""
    # rres = trunc(sqrt(xres^2 + yres^2)/2)  -- maximum in-image radius in pixels
    rres = int(math.sqrt(xres * xres + yres * yres) / 2.0)
    # ares = round(pi*max(xres, yres)) rounded up to an even number
    ar = int(math.floor(math.pi * max(xres, yres) + 0.5))
    ares = ar + (ar & 1)
    return rres, ares


def _to_polar(data: np.ndarray, rres: int, ares: int, order: int) -> np.ndarray:
    """Remap the image to polar (r, phi) coordinates, center at pixel (xres/2, yres/2).

    Uses polar remapping with linear interpolation and border-extension
    exterior.  Rows are the angle phi (one full revolution in ``ares`` steps),
    columns are the radius in pixels.
    """
    yres, xres = data.shape
    phiscale = 2.0 * math.pi / ares
    p = np.arange(rres, dtype=np.float64)                   # radius in pixels
    theta = np.arange(ares, dtype=np.float64) * phiscale    # angle index
    coords = np.empty((2, ares, rres), dtype=np.float64)
    # Source pixel-space coordinates: column = xres/2 + p*cos(theta),
    # row = yres/2 + p*sin(theta).
    coords[1] = xres / 2.0 + p[np.newaxis, :] * np.cos(theta[:, np.newaxis])
    coords[0] = yres / 2.0 + p[np.newaxis, :] * np.sin(theta[:, np.newaxis])
    return map_coordinates(data, coords, order=order, mode="nearest")


def _from_polar(polar: np.ndarray, rres: int, ares: int, order: int,
                xres: int, yres: int) -> np.ndarray:
    """Remap the smoothed polar field back to the image.

    The returned image pixel (j, i) samples the polar field at
    column sqrt((j - xres/2)^2 + (i - yres/2)^2) - 0.5 and
    row 1.5*ares + atan2(-ry, -rx)*ares/(2*pi), which lies in the second
    (periodically extended) half of the array.
    """
    phiscale = 2.0 * math.pi / ares
    j = np.arange(xres, dtype=np.float64) - xres / 2.0
    i = np.arange(yres, dtype=np.float64) - yres / 2.0
    rx = j[np.newaxis, :]
    ry = i[:, np.newaxis]
    coords = np.empty((2, yres, xres), dtype=np.float64)
    coords[0] = 1.5 * ares + np.arctan2(-ry, -rx) / phiscale
    coords[1] = np.sqrt(rx * rx + ry * ry) - 0.5
    return map_coordinates(polar, coords, order=order, mode="nearest")


@register_node(display_name="Radial Smoothing")
class RadialSmoothing:
    CATEGORY = "Geometry"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "sigma_r": ("FLOAT", {
                    "default": 10.0, "min": 0.0, "max": 1000.0, "step": 0.1,
                }),
                "sigma_phi_deg": ("FLOAT", {
                    "default": 10.0, "min": 0.0, "max": 360.0, "step": 0.1,
                }),
                "interpolation": (["linear", "cubic", "nearest"], {"default": "linear"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'smoothed'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Smooth an image in polar coordinates: sigma_r blurs along the radial "
        "direction (concentric circles), sigma_phi_deg blurs along the angular "
        "direction (constant distance from the center). The image is resampled "
        "to polar coordinates around its center, Gaussian-filtered, and mapped "
        "back. Any sigma set to zero disables that component."
    )

    KEYWORDS = ("smooth", "polar", "radial", "angular", "gaussian", "circular")

    def process(
        self,
        field: DataField,
        sigma_r: float,
        sigma_phi_deg: float,
        interpolation: str,
    ) -> tuple:
        if interpolation not in _INTERP_ORDER:
            raise ValueError(f"Unknown interpolation mode: {interpolation!r}")
        if sigma_r < 0.0 or sigma_phi_deg < 0.0:
            raise ValueError("Smoothing sigmas must be non-negative")

        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        order = _INTERP_ORDER[interpolation]

        rres, ares = _polar_dimensions(xres, yres)
        polar = _to_polar(data, rres, ares, order)

        # Extend periodically along the radius so the radial Gaussian at large
        # radii uses real data instead of the field border.
        nrep = ares // rres + 1
        polar_c = np.concatenate([polar, np.tile(polar, (1, nrep))[:, :ares]], axis=1)

        if sigma_r > 0.0:
            polar_c = gaussian_filter1d(polar_c, sigma_r, axis=1, mode="reflect", truncate=5.0)

        # Duplicate the angular range (extra 180 deg covers large angular sigmas
        # and keeps the back-mapping, which samples rows in [ares, 2*ares), away
        # from the phi seam).
        polar_c = np.concatenate([polar_c, polar_c], axis=0)
        if sigma_phi_deg > 0.0:
            sigma_phi = sigma_phi_deg / 360.0 * ares     # angular sigma in rows
            polar_c = gaussian_filter1d(polar_c, sigma_phi, axis=0, mode="reflect", truncate=5.0)

        result = _from_polar(polar_c, rres, ares, order, xres, yres)
        return (field.replace(data=result),)
