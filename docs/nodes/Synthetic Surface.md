# Synthetic Surface

Generate synthetic test surfaces for development, calibration, and algorithm testing. Equivalent to Gwyddion's *_synth.c modules.

## Outputs

| Name | Type | Description |
|------|------|-------------|
| surface | DATA_FIELD | Generated synthetic surface |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| pattern | dropdown | fbm | Pattern type: fbm, white_noise, lattice, steps, particles, flat |
| xres | INT | 256 | Horizontal resolution in pixels (16–2048) |
| yres | INT | 256 | Vertical resolution in pixels (16–2048) |
| xreal | FLOAT | 1e-6 | Physical width in metres |
| yreal | FLOAT | 1e-6 | Physical height in metres |
| amplitude | FLOAT | 1e-9 | Peak-to-peak amplitude in metres |
| seed | INT | 42 | Random seed for reproducibility (0–999999) |
| hurst_exponent | FLOAT | 0.7 | FBM roughness exponent: 0 = rough, 1 = smooth (fbm only) |
| lattice_spacing | FLOAT | 100e-9 | Lattice period in metres (lattice only) |
| lattice_angle | FLOAT | 90.0 | Angle between lattice vectors in degrees (lattice only) |
| n_steps | INT | 5 | Number of step terraces (steps only) |
| n_particles | INT | 20 | Number of particles (particles only) |
| particle_radius_px | INT | 10 | Particle radius in pixels (particles only) |

## Notes

- **fbm**: Fractional Brownian motion via spectral synthesis. Hurst exponent controls roughness.
- **white_noise**: Gaussian random noise.
- **lattice**: Two-axis sinusoidal grid with configurable spacing and angle.
- **steps**: Terraced step structure with equal step heights.
- **particles**: Random spherical particles on a flat background.
- **flat**: Zero surface (useful as a baseline).
- All patterns are normalised to the specified amplitude range.
