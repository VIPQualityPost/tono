"""
Test the FFT2D node against known inputs and Gwyddion-equivalent results.

Run from project root:
    python -m tests.test_fft
"""
import sys
import numpy as np

sys.path.insert(0, ".")
from backend.data_types import DataField
from backend.nodes.analysis import FFT2D


def make_field(data, xreal=1e-6, yreal=1e-6):
    """Create a DataField from a 2D array."""
    return DataField(data=data, xreal=xreal, yreal=yreal, si_unit_xy="m", si_unit_z="m")


def test_dc_removal():
    """A constant image should produce near-zero FFT after mean subtraction."""
    print("=== Test: DC removal ===")
    data = np.ones((64, 64)) * 42.0
    field = make_field(data)
    node = FFT2D()

    result, = node.process(field, windowing="none", level="mean", output="magnitude")
    peak = result.data.max()
    print(f"  Peak magnitude after mean subtraction of constant image: {peak:.2e}")
    assert peak < 1e-10, f"Expected ~0, got {peak}"
    print("  PASS\n")


def test_single_frequency():
    """A pure sine wave should produce two peaks at the known frequency."""
    print("=== Test: Single frequency detection ===")
    N = 128
    xreal = 1e-6  # 1 micron
    freq_cycles = 10  # 10 cycles across the image

    x = np.linspace(0, 1, N, endpoint=False)
    data = np.sin(2 * np.pi * freq_cycles * x)[np.newaxis, :] * np.ones((N, 1))
    field = make_field(data, xreal=xreal, yreal=xreal)

    node = FFT2D()
    result, = node.process(field, windowing="none", level="mean", output="magnitude")

    # The peak should be at column offset = freq_cycles from center
    mag = result.data
    cy, cx = N // 2, N // 2  # center (DC)

    # Find the peak location (excluding DC which should be ~0 after mean sub)
    mag_copy = mag.copy()
    mag_copy[cy, cx] = 0
    peak_idx = np.unravel_index(np.argmax(mag_copy), mag.shape)
    peak_col_offset = abs(peak_idx[1] - cx)

    print(f"  Image: {N}x{N}, {freq_cycles} horizontal cycles")
    print(f"  Expected peak at column offset {freq_cycles} from center")
    print(f"  Found peak at {peak_idx} (offset {peak_col_offset})")
    print(f"  DC value: {mag[cy, cx]:.2e}")
    print(f"  Peak value: {mag[peak_idx]:.2e}")
    assert peak_col_offset == freq_cycles, f"Expected offset {freq_cycles}, got {peak_col_offset}"
    assert peak_idx[0] == cy, f"Expected peak on center row, got row {peak_idx[0]}"
    print("  PASS\n")


def test_2d_frequency():
    """A 2D sine should produce peaks at the correct (kx, ky) position."""
    print("=== Test: 2D frequency detection ===")
    N = 128
    fx, fy = 8, 5  # cycles in x and y

    y, x = np.mgrid[0:N, 0:N] / N
    data = np.sin(2 * np.pi * (fx * x + fy * y))
    field = make_field(data)

    node = FFT2D()
    result, = node.process(field, windowing="none", level="mean", output="magnitude")
    mag = result.data

    cy, cx = N // 2, N // 2
    mag_copy = mag.copy()
    mag_copy[cy, cx] = 0
    peak_idx = np.unravel_index(np.argmax(mag_copy), mag.shape)

    dx = abs(peak_idx[1] - cx)
    dy = abs(peak_idx[0] - cy)

    print(f"  Input: sin(2π({fx}x + {fy}y))")
    print(f"  Expected peak offset: ({fy}, {fx}) from center")
    print(f"  Found peak at {peak_idx} (offset dy={dy}, dx={dx})")
    assert dx == fx and dy == fy, f"Expected ({fy},{fx}), got ({dy},{dx})"
    print("  PASS\n")


def test_psdf_normalization():
    """
    PSDF of white noise should integrate to the variance.

    Parseval's theorem: sum of PSDF * dk_x * dk_y ≈ variance of the signal.
    """
    print("=== Test: PSDF normalization (Parseval) ===")
    N = 256
    xreal = 1e-6
    rng = np.random.default_rng(42)
    data = rng.standard_normal((N, N))
    variance = data.var()

    field = make_field(data, xreal=xreal, yreal=xreal)
    node = FFT2D()

    result, = node.process(field, windowing="none", level="none", output="psdf")
    psdf = result.data

    # Integrate: sum of PSDF * dk_x * dk_y
    # Our output field has xreal = 2π*N/xreal (angular freq range)
    dk_x = result.xreal / N
    dk_y = result.yreal / N
    integral = psdf.sum() * dk_x * dk_y

    ratio = integral / variance
    print(f"  Signal variance: {variance:.6f}")
    print(f"  PSDF integral:   {integral:.6f}")
    print(f"  Ratio (should be ~1.0): {ratio:.4f}")
    # Allow 20% tolerance for finite-size effects
    assert 0.8 < ratio < 1.2, f"Parseval's theorem violated: ratio = {ratio}"
    print("  PASS\n")


def test_windowing_reduces_leakage():
    """Windowing should reduce spectral leakage from a non-integer frequency."""
    print("=== Test: Windowing reduces leakage ===")
    N = 128
    freq = 10.5  # non-integer → spectral leakage without windowing

    x = np.linspace(0, 1, N, endpoint=False)
    data = np.sin(2 * np.pi * freq * x)[np.newaxis, :] * np.ones((N, 1))
    field = make_field(data)

    node = FFT2D()

    # Without windowing
    r_none, = node.process(field, windowing="none", level="mean", output="magnitude")
    mag_none = r_none.data[N // 2, :]  # center row

    # With Hann windowing
    r_hann, = node.process(field, windowing="hann", level="mean", output="magnitude")
    mag_hann = r_hann.data[N // 2, :]

    # Measure leakage: ratio of energy far from peak vs total
    peak_col = np.argmax(mag_none)
    far_mask = np.ones(N, dtype=bool)
    far_mask[max(0, peak_col - 3):peak_col + 4] = False
    # Also mask the symmetric peak
    sym_col = N - peak_col
    far_mask[max(0, sym_col - 3):sym_col + 4] = False

    leakage_none = mag_none[far_mask].sum() / mag_none.sum()
    leakage_hann = mag_hann[far_mask].sum() / mag_hann.sum()

    print(f"  Non-integer frequency: {freq}")
    print(f"  Leakage without windowing: {leakage_none:.4f}")
    print(f"  Leakage with Hann window:  {leakage_hann:.4f}")
    assert leakage_hann < leakage_none, "Hann window should reduce leakage"
    print("  PASS\n")


def test_plane_subtraction():
    """Plane subtraction should remove linear gradients."""
    print("=== Test: Plane subtraction ===")
    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    # Tilted plane + sine wave
    data = 100 * x + 50 * y + np.sin(2 * np.pi * 8 * x)
    field = make_field(data)

    node = FFT2D()

    # Without leveling — huge DC and low-freq energy
    r_none, = node.process(field, windowing="none", level="none", output="magnitude")
    dc_none = r_none.data[N // 2, N // 2]

    # With mean subtraction — DC removed but gradient leaks
    r_mean, = node.process(field, windowing="none", level="mean", output="magnitude")
    dc_mean = r_mean.data[N // 2, N // 2]

    # With plane subtraction — gradient removed
    r_plane, = node.process(field, windowing="none", level="plane", output="magnitude")
    dc_plane = r_plane.data[N // 2, N // 2]

    # With plane subtraction, check the low-freq energy near DC is reduced
    # (plane subtraction removes gradients that leak into low frequencies)
    r = 3  # radius around DC to check
    cy, cx = N // 2, N // 2
    lowfreq_none = r_none.data[cy-r:cy+r+1, cx-r:cx+r+1].sum()
    lowfreq_plane = r_plane.data[cy-r:cy+r+1, cx-r:cx+r+1].sum()

    print(f"  DC magnitude (no leveling):    {dc_none:.2e}")
    print(f"  DC magnitude (mean subtract):  {dc_mean:.2e}")
    print(f"  DC magnitude (plane subtract): {dc_plane:.2e}")
    print(f"  Low-freq energy (no level):    {lowfreq_none:.2e}")
    print(f"  Low-freq energy (plane sub):   {lowfreq_plane:.2e}")
    assert dc_mean < dc_none, "Mean subtraction should reduce DC"
    assert lowfreq_plane < lowfreq_none * 0.01, "Plane subtraction should reduce low-freq energy"
    print("  PASS\n")


def test_non_square():
    """FFT should work on non-square, non-power-of-2 images."""
    print("=== Test: Non-square image ===")
    data = np.random.default_rng(99).standard_normal((100, 150))
    field = make_field(data, xreal=1.5e-6, yreal=1.0e-6)
    node = FFT2D()

    result, = node.process(field, windowing="hann", level="mean", output="log_magnitude")
    assert result.data.shape == (100, 150), f"Shape mismatch: {result.data.shape}"
    assert np.all(np.isfinite(result.data)), "Non-finite values in output"
    print(f"  Shape: {result.data.shape}")
    print(f"  Output range: [{result.data.min():.4f}, {result.data.max():.4f}]")
    print("  PASS\n")


def test_log_magnitude_visual_range():
    """Log magnitude should produce a reasonable dynamic range for display."""
    print("=== Test: Log magnitude visual range ===")
    N = 128
    x = np.linspace(0, 1, N, endpoint=False)
    # Multi-frequency test image
    y, x = np.mgrid[0:N, 0:N] / N
    data = (np.sin(2 * np.pi * 5 * x) +
            0.5 * np.sin(2 * np.pi * 15 * x + 2 * np.pi * 10 * y) +
            0.1 * np.random.default_rng(7).standard_normal((N, N)))
    field = make_field(data)

    node = FFT2D()
    result, = node.process(field, windowing="hann", level="mean", output="log_magnitude")

    vmin, vmax = result.data.min(), result.data.max()
    dynamic_range = vmax - vmin if vmin > 0 else vmax / max(abs(vmin), 1e-30)

    print(f"  Log magnitude range: [{vmin:.4f}, {vmax:.4f}]")
    print(f"  Dynamic range: {dynamic_range:.2f}")
    assert vmax > vmin, "Log magnitude should have nonzero range"
    assert np.all(np.isfinite(result.data)), "Non-finite values in log magnitude"
    print("  PASS\n")


if __name__ == "__main__":
    test_dc_removal()
    test_single_frequency()
    test_2d_frequency()
    test_psdf_normalization()
    test_windowing_reduces_leakage()
    test_plane_subtraction()
    test_non_square()
    test_log_magnitude_visual_range()
    print("All tests passed!")
