#!/usr/bin/env python3
"""
Example: using tono as a standalone signal processing library.

Run from the repo root:
    python examples/library_usage.py
"""

import numpy as np
import tono

# ── 1. Generate a synthetic surface ──────────────────────────────────

print("Generating synthetic surface...")
surface = tono.SyntheticSurface(
    pattern="fbm",
    xres=256,
    yres=256,
    xreal=10e-6,   # 10 um
    yreal=10e-6,
    amplitude=50e-9,  # 50 nm height range
    seed=42,
)
print(f"  Shape: {surface.data.shape}")
print(f"  Physical size: {surface.xreal*1e6:.1f} x {surface.yreal*1e6:.1f} um")
print(f"  Height range: {np.ptp(surface.data)*1e9:.1f} nm")

# ── 2. Level the surface ─────────────────────────────────────────────

print("\nLeveling...")
leveled = tono.PlaneLevelField(surface)
print(f"  Mean after leveling: {leveled.data.mean()*1e9:.4f} nm")

# ── 3. Apply a Gaussian filter ───────────────────────────────────────

print("\nFiltering...")
filtered = tono.GaussianFilter(leveled, sigma=2.0)
print(f"  Height range after filtering: {np.ptp(filtered.data)*1e9:.1f} nm")

# ── 4. Compute statistics ────────────────────────────────────────────

print("\nStatistics:")
table = tono.Statistics(filtered)
for row in table:
    print(f"  {row['quantity']}: {row['value']:.6g} {row.get('unit', '')}")

# ── 5. Edge detection ────────────────────────────────────────────────

print("\nEdge detection...")
edges = tono.EdgeDetect(filtered, method="sobel", sigma=1.0)
print(f"  Edge map range: [{edges.data.min():.2f}, {edges.data.max():.2f}]")

# ── 6. Create a DataField from a numpy array ─────────────────────────

print("\nCreating field from numpy array...")
data = np.sin(np.linspace(0, 4 * np.pi, 128).reshape(1, -1)) * \
       np.cos(np.linspace(0, 6 * np.pi, 128).reshape(-1, 1))
custom_field = tono.field(data, xreal=5e-6, yreal=5e-6, si_unit_z="V")
print(f"  Shape: {custom_field.data.shape}")
print(f"  Unit: {custom_field.si_unit_z}")

# ── 7. FFT analysis ──────────────────────────────────────────────────

print("\nFFT of the filtered surface...")
fft_log_mag, fft_mag, fft_phase, fft_psdf = tono.FFT2D(filtered, windowing="hann", level="mean")
print(f"  FFT shape: {fft_mag.data.shape}")
print(f"  Domain: {fft_mag.domain}")

# ── 8. List available nodes ──────────────────────────────────────────

all_nodes = tono.nodes()
print(f"\nTotal available nodes: {len(all_nodes)}")
print("First 10:", ", ".join(all_nodes[:10]))

print("\nDone!")
