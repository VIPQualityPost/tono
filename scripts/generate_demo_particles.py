#!/usr/bin/env python3
"""Generate a synthetic nanoparticle image for the demo/ folder.

The image simulates an AFM scan of particles on a flat substrate:
  - Slightly noisy background
  - ~20 hemisphere-shaped particles with varying radii and heights
  - Saved as both .npy (calibrated float64) and .png (visual preview)

Run from project root:
    python scripts/generate_demo_particles.py
"""

import numpy as np
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
DEMO_DIR.mkdir(exist_ok=True)

RNG = np.random.default_rng(2024)

# --- Image parameters ---
N = 256                         # pixels
SCAN_SIZE = 5e-6                # 5 µm scan
PIXEL_SIZE = SCAN_SIZE / N      # metres per pixel
BG_NOISE_RMS = 0.3e-9           # 0.3 nm background noise

# --- Generate particles ---
particles = []
# Hand-placed cluster + random scatter to give a realistic spread
fixed = [
    # (cx_frac, cy_frac, radius_nm, height_nm)
    (0.25, 0.30, 120, 30),
    (0.28, 0.34,  80, 20),
    (0.70, 0.25, 150, 45),
    (0.50, 0.55, 100, 25),
    (0.55, 0.60,  60, 15),
    (0.15, 0.75, 200, 55),
    (0.80, 0.80,  90, 22),
]
for cx_f, cy_f, r_nm, h_nm in fixed:
    particles.append((cx_f * N, cy_f * N, r_nm * 1e-9, h_nm * 1e-9))

# Random particles
for _ in range(15):
    cx = RNG.uniform(20, N - 20)
    cy = RNG.uniform(20, N - 20)
    radius = RNG.uniform(30, 180) * 1e-9   # 30–180 nm
    height = RNG.uniform(8, 60) * 1e-9     # 8–60 nm
    particles.append((cx, cy, radius, height))

# --- Render height map ---
image = RNG.normal(0, BG_NOISE_RMS, (N, N))

yy, xx = np.mgrid[0:N, 0:N]

for cx, cy, radius_m, height_m in particles:
    radius_px = radius_m / PIXEL_SIZE
    dist2 = (xx - cx) ** 2 + (yy - cy) ** 2
    inside = dist2 < radius_px ** 2
    # Hemisphere profile: z = h * sqrt(1 - (r/R)^2)
    z = np.zeros_like(image)
    z[inside] = height_m * np.sqrt(1.0 - dist2[inside] / radius_px ** 2)
    image = np.maximum(image, z)  # particles don't subtract from each other

# --- Save .npy (float64 metres) ---
npy_path = DEMO_DIR / "nanoparticles.npy"
np.save(str(npy_path), image)
print(f"Saved {npy_path}  shape={image.shape}  range=[{image.min():.2e}, {image.max():.2e}] m")

# --- Save .png (8-bit grayscale for quick visual) ---
from PIL import Image

normed = (image - image.min()) / (image.max() - image.min())
uint8 = (normed * 255).astype(np.uint8)
png_path = DEMO_DIR / "nanoparticles.png"
Image.fromarray(uint8, mode="L").save(str(png_path))
print(f"Saved {png_path}")

print(f"\n{len(particles)} particles generated on a {SCAN_SIZE*1e6:.0f} µm × {SCAN_SIZE*1e6:.0f} µm scan")
