"""Synthetic surface generation — create test surfaces for development and calibration."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField


# ---------------------------------------------------------------------------
# Original generators
# ---------------------------------------------------------------------------

def _fbm_surface(shape, rng, H=0.7):
    """Fractional Brownian motion surface via spectral synthesis."""
    yres, xres = shape
    kx = np.fft.fftfreq(xres)
    ky = np.fft.fftfreq(yres)
    KX, KY = np.meshgrid(kx, ky)
    K = np.sqrt(KX**2 + KY**2)
    K[0, 0] = 1.0
    power = K ** (-(H + 1.0))
    power[0, 0] = 0.0
    phases = rng.uniform(0, 2 * np.pi, shape)
    amplitudes = rng.standard_normal(shape)
    fft_data = amplitudes * np.sqrt(power) * np.exp(1j * phases)
    return np.real(np.fft.ifft2(fft_data))


def _lattice_surface(shape, xreal, yreal, spacing, angle_deg):
    """Periodic lattice (sinusoidal grid)."""
    yres, xres = shape
    x = np.linspace(0, xreal, xres, endpoint=False)
    y = np.linspace(0, yreal, yres, endpoint=False)
    X, Y = np.meshgrid(x, y)
    theta = np.radians(angle_deg)
    k = 2 * np.pi / spacing
    return np.cos(k * X) + np.cos(k * (X * np.cos(theta) + Y * np.sin(theta)))


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


# ---------------------------------------------------------------------------
# New generators
# ---------------------------------------------------------------------------

def _columnar_surface(shape, rng, n, radius):
    """Columnar growth — Gaussian pillars at random positions."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    sigma2 = max(1.0, float(radius) ** 2)
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.3, 1.0)
        r2 = (yy - cy) ** 2 + (xx - cx) ** 2
        surface += h * np.exp(-r2 / (2.0 * sigma2))
    return surface


def _objects_surface(shape, rng, n, size, obj_shape):
    """Random geometric objects (sphere, pyramid, box, cylinder, cone)."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    s = max(float(size), 1.0)
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.5, 1.0)
        dy = (yy - cy).astype(np.float64)
        dx = (xx - cx).astype(np.float64)
        r = np.sqrt(dy ** 2 + dx ** 2)
        if obj_shape == "pyramid":
            bump = np.maximum(1.0 - np.maximum(np.abs(dy), np.abs(dx)) / s, 0.0)
        elif obj_shape == "box":
            bump = ((np.abs(dy) <= s) & (np.abs(dx) <= s)).astype(np.float64)
        elif obj_shape == "cylinder":
            bump = (r <= s).astype(np.float64)
        elif obj_shape == "cone":
            bump = np.maximum(1.0 - r / s, 0.0)
        else:  # sphere
            bump = np.sqrt(np.maximum(s ** 2 - dy ** 2 - dx ** 2, 0.0)) / s
        surface = np.maximum(surface, h * bump)
    return surface


def _fibres_surface(shape, rng, n, length, width):
    """Randomly oriented fibre/line features."""
    yres, xres = shape
    surface = np.zeros(shape)
    yy, xx = np.mgrid[:yres, :xres]
    for _ in range(n):
        cy, cx = rng.uniform(0, yres), rng.uniform(0, xres)
        angle = rng.uniform(0, np.pi)
        h = rng.uniform(0.5, 1.0)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        along = (xx - cx) * cos_a + (yy - cy) * sin_a
        across = -(xx - cx) * sin_a + (yy - cy) * cos_a
        mask = (np.abs(along) <= length / 2) & (np.abs(across) <= width)
        surface = np.maximum(surface, h * mask.astype(np.float64))
    return surface


def _waves_surface(shape, rng, n_sources, frequency):
    """Superposition of decaying circular waves from random sources."""
    yres, xres = shape
    xn = np.arange(xres, dtype=np.float64) / max(xres - 1, 1)
    yn = np.arange(yres, dtype=np.float64) / max(yres - 1, 1)
    X, Y = np.meshgrid(xn, yn)
    surface = np.zeros(shape)
    for _ in range(n_sources):
        sx, sy = rng.random(), rng.random()
        amp = rng.uniform(0.5, 1.0)
        r = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
        surface += amp * np.exp(-3.0 * r) * np.cos(2 * np.pi * frequency * r)
    return surface


def _dunes_surface(shape, rng, frequency, direction_deg):
    """Asymmetric dune-like rippled surface."""
    yres, xres = shape
    theta = np.radians(direction_deg)
    xn = np.arange(xres, dtype=np.float64) / max(xres - 1, 1)
    yn = np.arange(yres, dtype=np.float64) / max(yres - 1, 1)
    X, Y = np.meshgrid(xn, yn)
    phase = frequency * (X * np.cos(theta) + Y * np.sin(theta))
    frac = phase - np.floor(phase)
    profile = np.where(frac < 0.7, frac / 0.7, (1.0 - frac) / 0.3)
    return profile + rng.standard_normal(shape) * 0.03


def _domains_surface(shape, rng, n_iterations):
    """Phase-separated domains via 2D Ising model (checkerboard Metropolis)."""
    yres, xres = shape
    spins = rng.choice([-1.0, 1.0], size=shape)
    beta = 0.55
    y, x = np.ogrid[:yres, :xres]
    for _ in range(n_iterations):
        for parity in range(2):
            mask = ((y + x) % 2 == parity)
            neighbors = (np.roll(spins, 1, axis=0) + np.roll(spins, -1, axis=0) +
                         np.roll(spins, 1, axis=1) + np.roll(spins, -1, axis=1))
            dE = 2.0 * spins * neighbors
            flip = (dE <= 0) | (rng.random(shape) < np.exp(np.minimum(-beta * dE, 0.0)))
            spins = np.where(mask & flip, -spins, spins)
    return spins


def _ballistic_surface(shape, rng, n_iterations):
    """Ballistic deposition with neighbor adhesion (vectorised)."""
    heights = np.zeros(shape)
    for _ in range(n_iterations):
        drops = rng.random(shape) > 0.7
        padded = np.pad(heights, 1, mode='wrap')
        neighbor_max = np.maximum.reduce([
            padded[:-2, 1:-1], padded[2:, 1:-1],
            padded[1:-1, :-2], padded[1:-1, 2:],
        ])
        heights = np.where(drops, np.maximum(heights, neighbor_max) + 1, heights)
    return heights


def _deposition_surface(shape, rng, n, radius):
    """Particle stacking — spheres deposited with gravity."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        r2 = ((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float64)
        h_sphere = np.sqrt(np.maximum(float(radius) ** 2 - r2, 0.0))
        footprint = h_sphere > 0
        base = float(surface[footprint].max()) if footprint.any() else 0.0
        surface = np.maximum(surface, base + h_sphere)
    return surface


def _rods_surface(shape, rng, n, length, width):
    """Rod/wire features with rounded (semicircular) cross-section."""
    yres, xres = shape
    surface = np.zeros(shape)
    yy, xx = np.mgrid[:yres, :xres]
    w = max(float(width), 1.0)
    for _ in range(n):
        cy, cx = rng.uniform(0, yres), rng.uniform(0, xres)
        angle = rng.uniform(0, np.pi)
        h = rng.uniform(0.5, 1.0)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        along = (xx - cx) * cos_a + (yy - cy) * sin_a
        across = (-(xx - cx) * sin_a + (yy - cy) * cos_a).astype(np.float64)
        in_rod = (np.abs(along) <= length / 2).astype(np.float64)
        profile = np.sqrt(np.maximum(w ** 2 - across ** 2, 0.0)) / w
        surface = np.maximum(surface, h * profile * in_rod)
    return surface


def _dla_surface(shape, rng, n_iterations):
    """Diffusion-limited aggregation via iterative boundary growth."""
    from scipy.ndimage import binary_dilation
    grid = np.zeros(shape)
    grid[shape[0] // 2, shape[1] // 2] = 1.0
    struct = np.ones((3, 3), dtype=bool)
    for _ in range(n_iterations):
        dilated = binary_dilation(grid > 0, structure=struct)
        boundary = dilated & (grid == 0)
        candidates = np.argwhere(boundary)
        if len(candidates) == 0:
            break
        n_add = max(1, len(candidates) // 8)
        chosen = rng.choice(len(candidates), size=min(n_add, len(candidates)),
                            replace=False)
        for idx in chosen:
            grid[candidates[idx][0], candidates[idx][1]] = rng.uniform(0.5, 1.0)
    return grid


def _discs_surface(shape, rng, n, radius):
    """Flat-topped circular disc features."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.5, 1.0)
        r = np.sqrt(((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float64))
        surface = np.maximum(surface, h * (r <= radius).astype(np.float64))
    return surface


def _plateaus_surface(shape, rng, n, radius):
    """Flat-topped features with smooth (tanh) edges."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.5, 1.0)
        r = np.sqrt(((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float64))
        edge_w = max(float(radius) * 0.2, 1.0)
        bump = h * 0.5 * (1.0 - np.tanh(3.0 * (r - radius) / edge_w))
        surface = np.maximum(surface, np.maximum(bump, 0.0))
    return surface


def _pileups_surface(shape, rng, n, size):
    """Rounded rectangle pileup structures."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    s = max(float(size), 1.0)
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.5, 1.0)
        aspect = rng.uniform(0.5, 2.0)
        angle = rng.uniform(0, np.pi)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        dx = ((xx - cx) * cos_a + (yy - cy) * sin_a).astype(np.float64)
        dy = (-(xx - cx) * sin_a + (yy - cy) * cos_a).astype(np.float64)
        w, ht = s * aspect, s / aspect
        r = ((np.abs(dx) / max(w, 1.0)) ** 4 + (np.abs(dy) / max(ht, 1.0)) ** 4) ** 0.25
        surface = np.maximum(surface, h * np.maximum(1.0 - r, 0.0))
    return surface


def _annealing_surface(shape, rng, n_iterations):
    """Surface relaxation via simulated annealing (terrain smoothing)."""
    surface = rng.standard_normal(shape)
    for i in range(n_iterations):
        t = max(0.01, 1.0 - i / n_iterations)
        avg = (np.roll(surface, 1, 0) + np.roll(surface, -1, 0) +
               np.roll(surface, 1, 1) + np.roll(surface, -1, 1)) / 4.0
        surface += 0.2 * (avg - surface)
        surface += rng.standard_normal(shape) * t * 0.02
    return surface


def _voronoi_surface(shape, rng, n_sites):
    """Voronoi tessellation with random heights per cell."""
    yres, xres = shape
    sites_y = rng.uniform(0, yres, size=n_sites)
    sites_x = rng.uniform(0, xres, size=n_sites)
    heights = rng.uniform(0, 1, size=n_sites)
    yy, xx = np.mgrid[:yres, :xres]
    surface = np.zeros(shape)
    min_dist = np.full(shape, np.inf)
    for i in range(n_sites):
        dist = (yy - sites_y[i]) ** 2 + (xx - sites_x[i]) ** 2
        closer = dist < min_dist
        surface = np.where(closer, heights[i], surface)
        min_dist = np.where(closer, dist, min_dist)
    return surface


def _spinodal_surface(shape, rng, n_iterations):
    """Spinodal decomposition via Cahn-Hilliard equation (FFT-based)."""
    yres, xres = shape
    c = 0.5 + 0.05 * rng.standard_normal(shape)
    kx = np.fft.fftfreq(xres) * 2 * np.pi
    ky = np.fft.fftfreq(yres) * 2 * np.pi
    KX, KY = np.meshgrid(kx, ky)
    K2 = KX ** 2 + KY ** 2
    dt, eps2 = 0.5, 0.01
    denom = 1.0 + dt * eps2 * K2 ** 2
    for _ in range(n_iterations):
        mu_hat = np.fft.fft2(c ** 3 - c)
        c_hat = np.fft.fft2(c)
        c_hat = (c_hat - dt * K2 * mu_hat) / denom
        c = np.real(np.fft.ifft2(c_hat))
        np.clip(c, -2.0, 2.0, out=c)
    return c


def _pde_surface(shape, rng, n_iterations):
    """Gray-Scott reaction-diffusion Turing patterns."""
    Du, Dv, F, k = 0.16, 0.08, 0.035, 0.065
    u = np.ones(shape)
    v = np.zeros(shape)
    r = min(shape[0], shape[1]) // 8
    cy, cx = shape[0] // 2, shape[1] // 2
    y0, y1 = max(0, cy - r), min(shape[0], cy + r)
    x0, x1 = max(0, cx - r), min(shape[1], cx + r)
    seed_shape = (y1 - y0, x1 - x0)
    u[y0:y1, x0:x1] = 0.5 + 0.1 * rng.standard_normal(seed_shape)
    v[y0:y1, x0:x1] = 0.25 + 0.1 * rng.standard_normal(seed_shape)
    for _ in range(n_iterations):
        lu = (np.roll(u, 1, 0) + np.roll(u, -1, 0) +
              np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
        lv = (np.roll(v, 1, 0) + np.roll(v, -1, 0) +
              np.roll(v, 1, 1) + np.roll(v, -1, 1) - 4 * v)
        uvv = u * v * v
        u += Du * lu - uvv + F * (1.0 - u)
        v += Dv * lv + uvv - (F + k) * v
    return v


def _spectral_surface(shape, rng, exponent):
    """FFT with power-law spectrum: P(k) proportional to k^(-exponent)."""
    yres, xres = shape
    kx = np.fft.fftfreq(xres)
    ky = np.fft.fftfreq(yres)
    KX, KY = np.meshgrid(kx, ky)
    K = np.sqrt(KX ** 2 + KY ** 2)
    K[0, 0] = 1.0
    power = K ** (-exponent)
    power[0, 0] = 0.0
    phases = rng.uniform(0, 2 * np.pi, shape)
    magnitudes = rng.standard_normal(shape)
    fft_data = magnitudes * np.sqrt(power) * np.exp(1j * phases)
    return np.real(np.fft.ifft2(fft_data))


def _residues_surface(shape, rng, n, size):
    """Irregular elliptical deposits with random orientation."""
    surface = np.zeros(shape)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    for _ in range(n):
        cy, cx = rng.integers(0, shape[0]), rng.integers(0, shape[1])
        h = rng.uniform(0.3, 1.0)
        aspect = rng.uniform(0.3, 3.0)
        angle = rng.uniform(0, np.pi)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        dx = ((xx - cx) * cos_a + (yy - cy) * sin_a).astype(np.float64)
        dy = (-(xx - cx) * sin_a + (yy - cy) * cos_a).astype(np.float64)
        sx = max(size * aspect, 1.0)
        sy = max(size / aspect, 1.0)
        bump = h * np.exp(-2.0 * ((dx / sx) ** 2 + (dy / sy) ** 2))
        surface = np.maximum(surface, bump)
    return surface


def _noise_surface(shape, rng, noise_type):
    """Various noise distributions."""
    if noise_type == "poisson":
        return rng.poisson(lam=5.0, size=shape).astype(np.float64)
    elif noise_type == "exponential":
        return rng.exponential(scale=1.0, size=shape)
    elif noise_type == "uniform":
        return rng.uniform(0, 1, size=shape)
    elif noise_type == "salt_pepper":
        base = np.zeros(shape)
        base[rng.random(shape) > 0.95] = 1.0
        base[rng.random(shape) > 0.95] = -1.0
        return base
    return rng.standard_normal(shape)  # gaussian default


def _periodic_surface(shape, frequency, periodic_type):
    """Repeating tiling patterns."""
    yres, xres = shape
    xn = np.arange(xres, dtype=np.float64) / max(xres - 1, 1)
    yn = np.arange(yres, dtype=np.float64) / max(yres - 1, 1)
    X, Y = np.meshgrid(xn, yn)
    f = max(frequency, 0.1)
    if periodic_type == "hex":
        s = 1.0 / f
        r = np.sqrt(3) / 2
        cy = Y / (s * r)
        row = np.floor(cy)
        shift = (row % 2) * 0.5
        col = np.floor(X / s + shift)
        hx = (col - shift) * s
        hy = row * s * r
        return (np.sqrt((X - hx) ** 2 + (Y - hy) ** 2) < s * 0.35).astype(np.float64)
    elif periodic_type == "stripe":
        return (np.sin(2 * np.pi * f * X) > 0).astype(np.float64)
    elif periodic_type == "diamond":
        u = np.floor(f * (X + Y))
        v = np.floor(f * (X - Y))
        return ((u + v) % 2).astype(np.float64)
    elif periodic_type == "staircase":
        return np.floor(X * f * 2) / max(f, 0.1)
    elif periodic_type == "rings":
        r = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
        return (np.sin(2 * np.pi * f * r * 4) > 0).astype(np.float64)
    # checker (default)
    return ((np.floor(X * f * 2) + np.floor(Y * f * 2)) % 2).astype(np.float64)


def _wfr_surface(shape, rng, n_sources, frequency):
    """Concentric wavefronts (ripples) from random sources — no decay."""
    yres, xres = shape
    xn = np.arange(xres, dtype=np.float64) / max(xres - 1, 1)
    yn = np.arange(yres, dtype=np.float64) / max(yres - 1, 1)
    X, Y = np.meshgrid(xn, yn)
    surface = np.zeros(shape)
    for _ in range(n_sources):
        sx, sy = rng.random(), rng.random()
        r = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
        surface += np.cos(2 * np.pi * frequency * r)
    return surface / max(n_sources, 1)


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

@register_node(display_name="Synthetic Surface")
class SyntheticSurface:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pattern": ([
                    "fbm", "white_noise", "lattice", "steps", "particles", "flat",
                    "columnar", "objects", "fibres", "waves", "dunes",
                    "domains", "ballistic", "deposition", "rods", "dla",
                    "discs", "plateaus", "pileups", "annealing", "voronoi",
                    "spinodal", "pde", "spectral", "residues",
                    "noise", "periodic", "wfr",
                ], {"default": "fbm"}),
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
                "n_iterations": ("INT", {"default": 200, "min": 10, "max": 5000}),
                "direction_deg": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 360.0, "step": 1.0}),
                "feature_length_px": ("INT", {"default": 40, "min": 2, "max": 500}),
                "object_shape": (["sphere", "pyramid", "box", "cylinder", "cone"],
                                 {"default": "sphere"}),
                "noise_type": (["gaussian", "poisson", "exponential", "uniform", "salt_pepper"],
                               {"default": "gaussian"}),
                "periodic_type": (["checker", "hex", "stripe", "diamond", "staircase", "rings"],
                                  {"default": "checker"}),
                "spectral_exponent": ("FLOAT", {"default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}),
                "frequency": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 50.0, "step": 0.5}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'surface'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Generate synthetic test surfaces for development, calibration, and "
        "algorithm testing. 28 patterns covering noise, geometry, growth "
        "simulations, phase separation, reaction-diffusion, and tiling. "
        "Equivalent to Gwyddion's *_synth.c modules."
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
        n_iterations: int = 200,
        direction_deg: float = 0.0,
        feature_length_px: int = 40,
        object_shape: str = "sphere",
        noise_type: str = "gaussian",
        periodic_type: str = "checker",
        spectral_exponent: float = 2.0,
        frequency: float = 5.0,
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
        elif pattern == "columnar":
            data = _columnar_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "objects":
            data = _objects_surface(shape, rng, n_particles, particle_radius_px, object_shape)
        elif pattern == "fibres":
            data = _fibres_surface(shape, rng, n_particles, feature_length_px, particle_radius_px)
        elif pattern == "waves":
            data = _waves_surface(shape, rng, n_particles, frequency)
        elif pattern == "dunes":
            data = _dunes_surface(shape, rng, frequency, direction_deg)
        elif pattern == "domains":
            data = _domains_surface(shape, rng, n_iterations)
        elif pattern == "ballistic":
            data = _ballistic_surface(shape, rng, n_iterations)
        elif pattern == "deposition":
            data = _deposition_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "rods":
            data = _rods_surface(shape, rng, n_particles, feature_length_px, particle_radius_px)
        elif pattern == "dla":
            data = _dla_surface(shape, rng, n_iterations)
        elif pattern == "discs":
            data = _discs_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "plateaus":
            data = _plateaus_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "pileups":
            data = _pileups_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "annealing":
            data = _annealing_surface(shape, rng, n_iterations)
        elif pattern == "voronoi":
            data = _voronoi_surface(shape, rng, n_particles)
        elif pattern == "spinodal":
            data = _spinodal_surface(shape, rng, n_iterations)
        elif pattern == "pde":
            data = _pde_surface(shape, rng, n_iterations)
        elif pattern == "spectral":
            data = _spectral_surface(shape, rng, spectral_exponent)
        elif pattern == "residues":
            data = _residues_surface(shape, rng, n_particles, particle_radius_px)
        elif pattern == "noise":
            data = _noise_surface(shape, rng, noise_type)
        elif pattern == "periodic":
            data = _periodic_surface(shape, frequency, periodic_type)
        elif pattern == "wfr":
            data = _wfr_surface(shape, rng, n_particles, frequency)
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
