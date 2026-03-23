"""
Generate test images and their FFT outputs for visual comparison with Gwyddion.
Saves PNG files to tests/output/.

Run: .venv/bin/python -m tests.test_fft_visual
"""
import sys
import os
import numpy as np

sys.path.insert(0, ".")
from backend.data_types import DataField, datafield_to_uint8, encode_preview
from backend.nodes.analysis import FFT2D

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)


def save_field(field, name, colormap="viridis"):
    """Save a DataField as a PNG for visual inspection."""
    from PIL import Image
    arr = datafield_to_uint8(field, colormap)
    img = Image.fromarray(arr)
    path = os.path.join(OUT_DIR, f"{name}.png")
    img.save(path)
    print(f"  Saved {path} (range: [{field.data.min():.4g}, {field.data.max():.4g}])")


def make_field(data, xreal=1e-6, yreal=1e-6):
    return DataField(data=data, xreal=xreal, yreal=yreal)


def main():
    node = FFT2D()
    N = 256

    # --- Test 1: Multi-frequency sine waves ---
    print("Test 1: Multi-frequency sine waves")
    y, x = np.mgrid[0:N, 0:N] / N
    data = (np.sin(2 * np.pi * 10 * x)
            + 0.7 * np.sin(2 * np.pi * 25 * y)
            + 0.3 * np.sin(2 * np.pi * (15 * x + 8 * y)))
    field = make_field(data)
    save_field(field, "01_sines_input")

    for output_mode in ["log_magnitude", "magnitude", "psdf"]:
        result, = node.process(field, windowing="hann", level="mean", output=output_mode)
        save_field(result, f"01_sines_{output_mode}")

    # --- Test 2: Real-world-like surface with noise + tilt ---
    print("\nTest 2: Tilted surface with features")
    rng = np.random.default_rng(42)
    data = (50 * x + 30 * y               # tilt
            + np.sin(2 * np.pi * 20 * x)   # periodic feature
            + 0.5 * rng.standard_normal((N, N)))  # noise
    field = make_field(data)
    save_field(field, "02_surface_input")

    for level_mode in ["none", "mean", "plane"]:
        result, = node.process(field, windowing="hann", level=level_mode, output="log_magnitude")
        save_field(result, f"02_surface_fft_level_{level_mode}")

    # --- Test 3: Checkerboard pattern ---
    print("\nTest 3: Checkerboard")
    freq = 16
    data = np.sign(np.sin(2 * np.pi * freq * x) * np.sin(2 * np.pi * freq * y))
    field = make_field(data)
    save_field(field, "03_checker_input")

    result, = node.process(field, windowing="none", level="mean", output="log_magnitude")
    save_field(result, "03_checker_fft")

    # --- Test 4: Concentric rings (radial frequency) ---
    print("\nTest 4: Concentric rings")
    r = np.sqrt((x - 0.5)**2 + (y - 0.5)**2)
    data = np.sin(2 * np.pi * 30 * r)
    field = make_field(data)
    save_field(field, "04_rings_input")

    result, = node.process(field, windowing="hann", level="mean", output="log_magnitude")
    save_field(result, "04_rings_fft")

    # --- Test 5: Compare windowing effects ---
    print("\nTest 5: Windowing comparison")
    data = np.sin(2 * np.pi * 10.5 * x) + 0.5 * np.sin(2 * np.pi * 30.3 * y)
    field = make_field(data)
    save_field(field, "05_window_input")

    for win in ["none", "hann", "hamming", "blackman"]:
        result, = node.process(field, windowing=win, level="mean", output="log_magnitude")
        save_field(result, f"05_window_{win}")

    print(f"\nAll outputs saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
