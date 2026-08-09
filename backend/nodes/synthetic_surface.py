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
# Line noise (lno_synth.c)
# ---------------------------------------------------------------------------

_SQRT2 = float(np.sqrt(2.0))
_SQRT3 = float(np.sqrt(3.0))
_SQRT6 = float(np.sqrt(6.0))


def _gwy_round(value):
    """GWY_ROUND: floor(x + 0.5), scalar or array."""
    return np.floor(np.asarray(value, dtype=np.float64) + 0.5)


def _point_noise(rng, n, distribution, direction, sigma=1.0):
    """Sample line-noise point noise like lno_synth.c's generators[].

    The distributions are centred with RMS sigma; direction mirrors the
    symmetrical/up/down noise-sign variants.
    """
    if distribution == "gaussian":
        x = rng.normal(0.0, sigma, n)
    elif distribution == "exponential":
        u = np.maximum(rng.random(n), np.finfo(np.float64).tiny)
        sign = rng.integers(0, 2, n, dtype=np.int64) * 2 - 1
        x = sign * sigma / _SQRT2 * np.log(u)
    elif distribution == "uniform":
        x = (2.0 * rng.random(n) - 1.0) * _SQRT3 * sigma
    elif distribution == "triangular":
        u = np.maximum(rng.random(n), np.finfo(np.float64).tiny)
        x = np.where(u <= 0.5, np.sqrt(2.0 * u) - 1.0,
                     1.0 - np.sqrt(2.0 * (1.0 - u))) * _SQRT6 * sigma
    else:
        raise ValueError(f"Unknown line-noise distribution: {distribution!r}")

    if direction == "up":
        return np.abs(x)
    if direction == "down":
        return -np.abs(x)
    return x


def _exp_noise_up(rng, n, sigma):
    """Absolute exponential (noise_exp_up): always >= 0."""
    u = np.maximum(rng.random(n), np.finfo(np.float64).tiny)
    return sigma / _SQRT2 * np.abs(np.log(u))


def _scan_xgrid(shape, lineprob):
    """x = (lineprob*(j + 0.5)/xres + i)/yres for every pixel."""
    yres, xres = shape
    cols = lineprob * (np.arange(xres, dtype=np.float64) + 0.5) / (xres * yres)
    return cols[np.newaxis, :] + np.arange(yres, dtype=np.float64)[:, np.newaxis] / yres


def _line_noise_steps(shape, rng, density, lineprob, scandir, cumulative,
                      distribution, direction):
    """Steps: random scan-direction steps, one per crossed position line.

    Ports lno_synth.c make_noise_steps(), including the stratified step
    positions and the cumulative vs. one-shot step heights.
    """
    yres, xres = shape
    nsteps = int(np.maximum(_gwy_round(yres * density), 1))
    # Stratified positions covering [0, 1) in batches of 64 like the C code.
    nbatches = (nsteps + 63) // 64
    pos = np.empty(nsteps)
    for ib in range(nbatches):
        base = ib * nsteps // nbatches
        nxt = (ib + 1) * nsteps // nbatches
        pos[base:nxt] = rng.uniform(base / nsteps, nxt / nsteps, nxt - base)
    pos = np.sort(pos)
    dh = _point_noise(rng, nsteps, distribution, direction)

    x = _scan_xgrid(shape, lineprob)
    idx = np.searchsorted(pos, x, side="left")   # steps crossed before x
    if cumulative:
        cum = np.concatenate(([0.0], np.cumsum(dh)))
        h = cum[np.minimum(idx, nsteps)]
    else:
        h = np.where(idx > 0, dh[np.maximum(idx - 1, 0)], 0.0)

    data = np.zeros(shape)
    if scandir == "LTR":
        data += h
    else:
        data[:, ::-1] += h
    return data


def _line_noise_scars(shape, rng, coverage, length, length_noise,
                      distribution, direction):
    """Scars: horizontal line segments with a constant height offset.

    Ports lno_synth.c make_noise_scars(), using the same scar count formula
    (stick-out correction, length dispersion) and per-segment constant heights.
    """
    yres, xres = shape
    n = xres * yres
    noise_corr = np.exp(length_noise * length_noise)
    stickout_corr = (length + xres) / length if length > 0 else 1.0
    nscars = int(np.maximum(_gwy_round(coverage * n * stickout_corr
                                       / (length * noise_corr)), 1))
    L = int(_gwy_round(length))

    # Uniform row/position draws equivalent to the C's rejected uint32 stream.
    i_param = yres * (xres + L)
    m = (0xFFFFFFFF // i_param) * i_param
    t = rng.integers(0, m, nscars)
    rows = t % yres
    j = (t // yres) % (xres + L) + L // 2 - L

    h = _point_noise(rng, nscars, distribution, direction)
    if length_noise:
        ln = rng.normal(0.0, length_noise, nscars)
        lens = np.maximum(_gwy_round(length * np.exp(ln)), 0).astype(np.int64)
    else:
        lens = np.full(nscars, L, dtype=np.int64)

    frm = np.clip(j - lens // 2, 0, xres - 1).astype(np.int64)
    to = np.clip(j + lens - lens // 2, 0, xres - 1).astype(np.int64)
    valid = frm <= to

    data = np.zeros((yres, xres + 1))
    rr = rows[valid]
    ff = frm[valid]
    tt = to[valid]
    hh = h[valid]
    np.add.at(data, (rr, ff), hh)
    np.add.at(data, (rr, tt + 1), -hh)
    return data[:, :xres]


def _line_noise_ridges(shape, rng, density, lineprob, scandir, width,
                       distribution, direction):
    """Ridges: ramps bounded by paired rising/falling events.

    Ports lno_synth.c make_noise_ridges() (ridge events sorted by position,
    heights accumulate as the scan crosses each event).
    """
    yres, xres = shape
    nridges = int(np.maximum(_gwy_round(yres * (1.0 + width) * density), 1))
    centre = rng.uniform(-width, 1.0 + width, nridges)
    w = _exp_noise_up(rng, nridges, width)
    dh = _point_noise(rng, nridges, distribution, direction)

    pos = np.concatenate([centre - w, centre + w])
    dhh = np.concatenate([dh, -dh])
    order = np.argsort(pos, kind="stable")
    pos = pos[order]
    dhh = dhh[order]

    x = _scan_xgrid(shape, lineprob)
    idx = np.searchsorted(pos, x, side="left")
    cum = np.concatenate(([0.0], np.cumsum(dhh)))
    h = cum[np.minimum(idx, dhh.size)]

    data = np.zeros(shape)
    if scandir == "LTR":
        data += h
    else:
        data[:, ::-1] += h
    return data


def _line_noise(shape, rng, ln_type, ln_distribution, ln_direction,
                density=1.0, lineprob=0.0, scandir="LTR", cumulative=False,
                coverage=0.01, length=10.0, length_noise=0.0, width=0.01):
    """Generate one of the line-noise structures (lno_synth.c)."""
    if ln_type == "steps":
        return _line_noise_steps(shape, rng, density, lineprob, scandir,
                                 cumulative, ln_distribution, ln_direction)
    if ln_type == "scars":
        return _line_noise_scars(shape, rng, coverage, length, length_noise,
                                 ln_distribution, ln_direction)
    if ln_type == "ridges":
        return _line_noise_ridges(shape, rng, density, lineprob, scandir,
                                  width, ln_distribution, ln_direction)
    raise ValueError(f"Unknown line-noise type: {ln_type!r}")


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
                    "noise", "periodic", "wfr", "line_noise",
                ], {"default": "fbm"}),
                "xres": ("INT", {"default": 256, "min": 16, "max": 2048}),
                "yres": ("INT", {"default": 256, "min": 16, "max": 2048}),
                "xreal": ("FLOAT", {"default": 1e-6, "min": 1e-9, "max": 1.0, "step": 1e-9}),
                "yreal": ("FLOAT", {"default": 1e-6, "min": 1e-9, "max": 1.0, "step": 1e-9}),
                "amplitude": ("FLOAT", {"default": 1e-9, "min": 0.0, "max": 1e-3, "step": 1e-10}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999}),
            },
            "optional": {
                "hurst_exponent": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05,
                    "show_when_widget_value": {"pattern": ["fbm"]},
                }),
                "lattice_spacing": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 1e-3, "step": 1e-9,
                    "show_when_widget_value": {"pattern": ["lattice"]},
                }),
                "lattice_angle": ("FLOAT", {
                    "default": 90.0, "min": 0.0, "max": 180.0, "step": 1.0,
                    "show_when_widget_value": {"pattern": ["lattice"]},
                }),
                "n_steps": ("INT", {
                    "default": 5, "min": 1, "max": 100,
                    "show_when_widget_value": {"pattern": ["steps"]},
                }),
                "n_particles": ("INT", {
                    "default": 20, "min": 1, "max": 500,
                    "show_when_widget_value": {"pattern": [
                        "particles", "columnar", "objects", "fibres", "waves",
                        "deposition", "rods", "discs", "plateaus", "pileups",
                        "voronoi", "residues", "wfr",
                    ]},
                }),
                "particle_radius_px": ("INT", {
                    "default": 10, "min": 2, "max": 100,
                    "show_when_widget_value": {"pattern": [
                        "particles", "columnar", "objects", "fibres",
                        "deposition", "rods", "discs", "plateaus", "pileups",
                        "residues",
                    ]},
                }),
                "n_iterations": ("INT", {
                    "default": 200, "min": 10, "max": 5000,
                    "show_when_widget_value": {"pattern": [
                        "domains", "ballistic", "dla", "annealing",
                        "spinodal", "pde",
                    ]},
                }),
                "direction_deg": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 360.0, "step": 1.0,
                    "show_when_widget_value": {"pattern": ["dunes"]},
                }),
                "feature_length_px": ("INT", {
                    "default": 40, "min": 2, "max": 500,
                    "show_when_widget_value": {"pattern": ["fibres", "rods"]},
                }),
                "object_shape": (["sphere", "pyramid", "box", "cylinder", "cone"], {
                    "default": "sphere",
                    "show_when_widget_value": {"pattern": ["objects"]},
                }),
                "noise_type": (["gaussian", "poisson", "exponential", "uniform", "salt_pepper"], {
                    "default": "gaussian",
                    "show_when_widget_value": {"pattern": ["noise"]},
                }),
                "periodic_type": (["checker", "hex", "stripe", "diamond", "staircase", "rings"], {
                    "default": "checker",
                    "show_when_widget_value": {"pattern": ["periodic"]},
                }),
                "spectral_exponent": ("FLOAT", {
                    "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1,
                    "show_when_widget_value": {"pattern": ["spectral"]},
                }),
                "frequency": ("FLOAT", {
                    "default": 5.0, "min": 0.5, "max": 50.0, "step": 0.5,
                    "show_when_widget_value": {"pattern": [
                        "waves", "dunes", "periodic", "wfr",
                    ]},
                }),
                "ln_type": (["steps", "scars", "ridges"], {
                    "default": "steps",
                    "show_when_widget_value": {"pattern": ["line_noise"]},
                }),
                "ln_distribution": (["gaussian", "exponential", "uniform", "triangular"], {
                    "default": "gaussian",
                    "show_when_widget_value": {"pattern": ["line_noise"]},
                }),
                "ln_direction": (["both", "up", "down"], {
                    "default": "both",
                    "show_when_widget_value": {"pattern": ["line_noise"]},
                }),
                "ln_density": ("FLOAT", {
                    "default": 1.0, "min": 5e-4, "max": 200.0, "step": 0.1,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["steps", "ridges"],
                    },
                }),
                "ln_lineprob": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["steps", "ridges"],
                    },
                }),
                "ln_scandir": (["LTR", "RTL"], {
                    "default": "LTR",
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["steps", "ridges"],
                    },
                }),
                "ln_cumulative": ("BOOLEAN", {
                    "default": False,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["steps"],
                    },
                }),
                "ln_coverage": ("FLOAT", {
                    "default": 0.01, "min": 1e-4, "max": 20.0, "step": 0.01,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["scars"],
                    },
                }),
                "ln_length": ("FLOAT", {
                    "default": 10.0, "min": 1.0, "max": 1e4, "step": 0.5,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["scars"],
                    },
                }),
                "ln_length_noise": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["scars"],
                    },
                }),
                "ln_width": ("FLOAT", {
                    "default": 0.01, "min": 1e-4, "max": 1.0, "step": 0.001,
                    "show_when_widget_value": {
                        "pattern": ["line_noise"], "ln_type": ["ridges"],
                    },
                }),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'surface'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Generate synthetic test surfaces for development, calibration, and "
        "algorithm testing. 29 patterns covering noise, geometry, growth "
        "simulations, phase separation, reaction-diffusion, tiling, and line "
        "noise. "
    )

    KEYWORDS = ("generate", "fbm", "fractal", "noise", "simulation", "test", "dla", "voronoi", "turing", "spinodal", "pattern", "line noise")

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
        ln_type: str = "steps",
        ln_distribution: str = "gaussian",
        ln_direction: str = "both",
        ln_density: float = 1.0,
        ln_lineprob: float = 0.0,
        ln_scandir: str = "LTR",
        ln_cumulative: bool = False,
        ln_coverage: float = 0.01,
        ln_length: float = 10.0,
        ln_length_noise: float = 0.0,
        ln_width: float = 0.01,
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
        elif pattern == "line_noise":
            data = _line_noise(
                shape, rng, ln_type, ln_distribution, ln_direction,
                density=ln_density, lineprob=ln_lineprob, scandir=ln_scandir,
                cumulative=ln_cumulative, coverage=ln_coverage,
                length=ln_length, length_noise=ln_length_noise, width=ln_width,
            )
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
