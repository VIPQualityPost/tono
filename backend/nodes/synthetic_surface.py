"""Synthetic surface generation — create test surfaces for development and calibration."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


def _fbm_surface(shape, rng, H=0.7):
    """Fractional Brownian motion surface via spectral synthesis."""
    yres, xres = shape
    kx = np.fft.fftfreq(xres)
    ky = np.fft.fftfreq(yres)
    KX, KY = np.meshgrid(kx, ky)
    K = np.sqrt(KX**2 + KY**2)
    K[0, 0] = 1.0  # avoid division by zero
    power = K ** (-(H + 1.0))
    power[0, 0] = 0.0

    phases = rng.uniform(0, 2 * np.pi, shape)
    amplitudes = rng.standard_normal(shape)
    fft_data = amplitudes * np.sqrt(power) * np.exp(1j * phases)
    surface = np.real(np.fft.ifft2(fft_data))
    return surface


def _lattice_surface(shape, xreal, yreal, spacing, angle_deg):
    """Periodic lattice (sinusoidal grid)."""
    yres, xres = shape
    x = np.linspace(0, xreal, xres, endpoint=False)
    y = np.linspace(0, yreal, yres, endpoint=False)
    X, Y = np.meshgrid(x, y)

    theta = np.radians(angle_deg)
    k = 2 * np.pi / spacing
    surface = np.cos(k * X) + np.cos(k * (X * np.cos(theta) + Y * np.sin(theta)))
    return surface


def _steps_surface(shape, n_steps):
    """Terraced step structure."""
    yres, xres = shape
    ramp = np.linspace(0, n_steps, xres, endpoint=False)
    steps = np.floor(ramp)
    return np.tile(steps, (yres, 1)).astype(np.float64)


def _particles_surface(shape, rng, n_particles, radius_px):
    """Random spherical particles on a flat background."""
    yres, xres = shape
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:yres, :xres]
    for _ in range(n_particles):
        cy = rng.integers(0, yres)
        cx = rng.integers(0, xres)
        r2 = (yy - cy)**2 + (xx - cx)**2
        height = np.sqrt(np.maximum(radius_px**2 - r2, 0.0))
        surface = np.maximum(surface, height)
    return surface


@register_node(display_name="Synthetic Surface")
class SyntheticSurface:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pattern": (["fbm", "white_noise", "lattice", "steps", "particles", "flat"],
                            {"default": "fbm"}),
                "xres": ("INT", {"default": 256, "min": 16, "max": 2048}),
                "yres": ("INT", {"default": 256, "min": 16, "max": 2048}),
                "xreal": ("FLOAT", {"default": 1e-6, "min": 1e-9, "max": 1.0, "step": 1e-9}),
                "yreal": ("FLOAT", {"default": 1e-6, "min": 1e-9, "max": 1.0, "step": 1e-9}),
                "amplitude": ("FLOAT", {"default": 1e-9, "min": 0.0, "max": 1e-3, "step": 1e-10}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999}),
            },
            "optional": {
                "hurst_exponent": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05}),
                "lattice_spacing": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 1e-3, "step": 1e-9,
                }),
                "lattice_angle": ("FLOAT", {"default": 90.0, "min": 0.0, "max": 180.0, "step": 1.0}),
                "n_steps": ("INT", {"default": 5, "min": 1, "max": 100}),
                "n_particles": ("INT", {"default": 20, "min": 1, "max": 500}),
                "particle_radius_px": ("INT", {"default": 10, "min": 2, "max": 100}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'surface'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Generate synthetic test surfaces for development, calibration, and "
        "algorithm testing. Patterns: fbm (fractional Brownian motion), "
        "white_noise, lattice (periodic grid), steps (terraced), "
        "particles (spherical bumps on flat), flat (zero surface). "
    )

    def process(
        self,
        pattern: str,
        xres: int,
        yres: int,
        xreal: float,
        yreal: float,
        amplitude: float,
        seed: int,
        hurst_exponent: float = 0.7,
        lattice_spacing: float = 100e-9,
        lattice_angle: float = 90.0,
        n_steps: int = 5,
        n_particles: int = 20,
        particle_radius_px: int = 10,
    ) -> tuple:
        shape = (yres, xres)
        rng = np.random.default_rng(seed)

        if pattern == "fbm":
            data = _fbm_surface(shape, rng, H=hurst_exponent)
        elif pattern == "white_noise":
            data = rng.standard_normal(shape)
        elif pattern == "lattice":
            data = _lattice_surface(shape, xreal, yreal, lattice_spacing, lattice_angle)
        elif pattern == "steps":
            data = _steps_surface(shape, n_steps)
        elif pattern == "particles":
            data = _particles_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "flat":
            data = np.zeros(shape)
        else:
            raise ValueError(f"Unknown pattern: {pattern!r}")

        # Normalise and scale by amplitude
        drange = data.max() - data.min()
        if drange > 0:
            data = (data - data.min()) / drange * amplitude
        else:
            data = np.zeros(shape)

        field = DataField(
            data=data,
            xreal=xreal,
            yreal=yreal,
            si_unit_xy="m",
            si_unit_z="m",
        )
        return (field,)
