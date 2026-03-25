"""
Tests for all argonode backend nodes (excluding FFT2D which has its own test file).

Run from project root:
    .venv/bin/python -m tests.test_nodes
"""
import sys
import os
import tempfile
import numpy as np

sys.path.insert(0, ".")
from backend.data_types import DataField


def make_field(data=None, shape=(64, 64), xreal=1e-6, yreal=1e-6):
    """Create a DataField, optionally from given data or a random field."""
    if data is None:
        data = np.random.default_rng(42).standard_normal(shape)
    return DataField(data=data, xreal=xreal, yreal=yreal, si_unit_xy="m", si_unit_z="m")


# =========================================================================
# Filters
# =========================================================================

def test_gaussian_filter():
    print("=== Test: GaussianFilter ===")
    from backend.nodes.filters import GaussianFilter
    node = GaussianFilter()
    field = make_field()

    result, = node.process(field, sigma=2.0)
    assert result.data.shape == field.data.shape
    assert result.xreal == field.xreal
    assert result.si_unit_z == field.si_unit_z
    # Gaussian blur should reduce variance
    assert result.data.std() < field.data.std()
    # With very small sigma, output should be nearly unchanged
    result_tiny, = node.process(field, sigma=0.01)
    assert np.allclose(result_tiny.data, field.data, atol=1e-6)
    print("  PASS\n")


def test_median_filter():
    print("=== Test: MedianFilter ===")
    from backend.nodes.filters import MedianFilter
    node = MedianFilter()

    # Median filter should remove salt-and-pepper noise
    data = np.zeros((64, 64))
    rng = np.random.default_rng(7)
    noise_idx = rng.choice(64 * 64, size=100, replace=False)
    data.ravel()[noise_idx] = 1.0
    field = make_field(data=data)

    result, = node.process(field, size=3)
    assert result.data.shape == field.data.shape
    # Should remove most impulse noise
    assert result.data.sum() < field.data.sum()
    # Size=1 should be identity
    result_1, = node.process(field, size=1)
    assert np.array_equal(result_1.data, field.data)
    print("  PASS\n")


def test_edge_detect():
    print("=== Test: EdgeDetect ===")
    from backend.nodes.filters import EdgeDetect
    node = EdgeDetect()

    # Create an image with a sharp vertical edge
    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)

    for method in ["sobel", "prewitt", "laplacian", "log"]:
        result, = node.process(field, method=method, sigma=1.0)
        assert result.data.shape == field.data.shape
        # Edge response should be strongest near column 32
        col_energy = np.abs(result.data).sum(axis=0)
        peak_col = np.argmax(col_energy)
        assert abs(peak_col - 32) <= 2, f"{method}: peak at col {peak_col}, expected ~32"

    print("  PASS\n")


def test_fft_filter_1d():
    print("=== Test: FFTFilter1D ===")
    from backend.nodes.filters import FFTFilter1D
    node = FFTFilter1D()

    # Signal: low-frequency sine + high-frequency sine
    n = 256
    t = np.arange(n, dtype=np.float64) / n
    low = np.sin(2 * np.pi * 3 * t)   # 3 cycles — low freq
    high = np.sin(2 * np.pi * 80 * t)  # 80 cycles — high freq
    line = low + high

    # Lowpass should keep low, suppress high
    filtered_lp, = node.process(line, filter_type="lowpass", cutoff=0.15, cutoff_high=0.4, order=4)
    assert len(filtered_lp) == n
    corr_low = np.corrcoef(filtered_lp, low)[0, 1]
    corr_high = np.corrcoef(filtered_lp, high)[0, 1]
    assert corr_low > 0.95, f"Lowpass: correlation with low={corr_low}"
    assert abs(corr_high) < 0.3, f"Lowpass: correlation with high={corr_high}"

    # Highpass should keep high, suppress low
    filtered_hp, = node.process(line, filter_type="highpass", cutoff=0.4, cutoff_high=0.4, order=4)
    corr_low_hp = np.corrcoef(filtered_hp, low)[0, 1]
    corr_high_hp = np.corrcoef(filtered_hp, high)[0, 1]
    assert abs(corr_low_hp) < 0.3, f"Highpass: correlation with low={corr_low_hp}"
    assert corr_high_hp > 0.95, f"Highpass: correlation with high={corr_high_hp}"

    # Bandpass centred on the high frequency
    filtered_bp, = node.process(line, filter_type="bandpass", cutoff=0.4, cutoff_high=0.8, order=4)
    corr_low_bp = np.corrcoef(filtered_bp, low)[0, 1]
    corr_high_bp = np.corrcoef(filtered_bp, high)[0, 1]
    assert abs(corr_low_bp) < 0.3, f"Bandpass: correlation with low={corr_low_bp}"
    assert corr_high_bp > 0.9, f"Bandpass: correlation with high={corr_high_bp}"

    # Notch (band-reject) centred on the high frequency — should remove it
    filtered_notch, = node.process(line, filter_type="notch", cutoff=0.4, cutoff_high=0.8, order=4)
    corr_low_notch = np.corrcoef(filtered_notch, low)[0, 1]
    corr_high_notch = np.corrcoef(filtered_notch, high)[0, 1]
    assert corr_low_notch > 0.95, f"Notch: correlation with low={corr_low_notch}"
    assert abs(corr_high_notch) < 0.3, f"Notch: correlation with high={corr_high_notch}"

    print("  PASS\n")


def test_fft_filter_2d():
    print("=== Test: FFTFilter2D ===")
    from backend.nodes.filters import FFTFilter2D
    node = FFTFilter2D()

    N = 128
    y, x = np.mgrid[0:N, 0:N] / N
    # Low-frequency 2D pattern + high-frequency pattern
    low_2d = np.sin(2 * np.pi * 3 * x) + np.sin(2 * np.pi * 3 * y)
    high_2d = np.sin(2 * np.pi * 40 * x) + np.sin(2 * np.pi * 40 * y)
    data = low_2d + high_2d
    field = make_field(data=data, shape=None, xreal=1e-6, yreal=1e-6)

    # Lowpass — should preserve low, remove high
    result_lp, = node.process(field, filter_type="lowpass", cutoff=0.15, cutoff_high=0.4, order=4)
    assert result_lp.data.shape == (N, N)
    assert result_lp.xreal == field.xreal
    assert result_lp.si_unit_z == field.si_unit_z
    corr_low = np.corrcoef(result_lp.data.ravel(), low_2d.ravel())[0, 1]
    corr_high = np.corrcoef(result_lp.data.ravel(), high_2d.ravel())[0, 1]
    assert corr_low > 0.9, f"2D lowpass: correlation with low={corr_low}"
    assert abs(corr_high) < 0.3, f"2D lowpass: correlation with high={corr_high}"

    # Highpass — should preserve high, remove low
    result_hp, = node.process(field, filter_type="highpass", cutoff=0.4, cutoff_high=0.4, order=4)
    corr_low_hp = np.corrcoef(result_hp.data.ravel(), low_2d.ravel())[0, 1]
    corr_high_hp = np.corrcoef(result_hp.data.ravel(), high_2d.ravel())[0, 1]
    assert abs(corr_low_hp) < 0.3, f"2D highpass: correlation with low={corr_low_hp}"
    assert corr_high_hp > 0.9, f"2D highpass: correlation with high={corr_high_hp}"

    # Constant field should be unchanged by lowpass (DC preservation)
    const = make_field(data=np.ones((32, 32)) * 7.0)
    result_const, = node.process(const, filter_type="lowpass", cutoff=0.5, cutoff_high=0.5, order=2)
    assert np.allclose(result_const.data, 7.0, atol=1e-10), "Lowpass should preserve constant field"

    print("  PASS\n")


# =========================================================================
# Level
# =========================================================================

def test_plane_level():
    print("=== Test: PlaneLevelField ===")
    from backend.nodes.level import PlaneLevelField
    node = PlaneLevelField()

    # Create a tilted plane + small signal
    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    signal = np.sin(2 * np.pi * 5 * x)
    data = 100 * x + 50 * y + signal
    field = make_field(data=data)

    result, = node.process(field)
    assert result.data.shape == field.data.shape
    # After plane leveling, mean should be near zero
    assert abs(result.data.mean()) < 1e-10
    # The signal should remain (correlation with original sine)
    corr = np.corrcoef(result.data.ravel(), signal.ravel())[0, 1]
    assert corr > 0.98, f"Signal correlation after leveling: {corr}"
    print("  PASS\n")


def test_poly_level():
    print("=== Test: PolyLevelField ===")
    from backend.nodes.level import PolyLevelField
    node = PolyLevelField()

    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    # Quadratic background + signal
    background = 50 * x**2 + 30 * y**2 + 10 * x * y
    signal = np.sin(2 * np.pi * 8 * x)
    data = background + signal
    field = make_field(data=data)

    leveled, bg = node.process(field, degree_x=2, degree_y=2)
    assert leveled.data.shape == field.data.shape
    assert bg.data.shape == field.data.shape
    # leveled + bg should reconstruct original
    assert np.allclose(leveled.data + bg.data, field.data, atol=1e-10)
    # Signal should be preserved after leveling
    corr = np.corrcoef(leveled.data.ravel(), signal.ravel())[0, 1]
    assert corr > 0.95, f"Signal correlation after poly leveling: {corr}"
    # Degree 0 should just subtract the mean
    leveled_0, bg_0 = node.process(field, degree_x=0, degree_y=0)
    assert abs(leveled_0.data.mean()) < 1e-10
    print("  PASS\n")


def test_fix_zero():
    print("=== Test: FixZero ===")
    from backend.nodes.level import FixZero
    node = FixZero()
    field = make_field(data=np.array([[10, 20], [30, 40]], dtype=np.float64))

    result_min, = node.process(field, method="min")
    assert result_min.data.min() == 0.0
    assert result_min.data.max() == 30.0

    result_mean, = node.process(field, method="mean")
    assert abs(result_mean.data.mean()) < 1e-10

    result_median, = node.process(field, method="median")
    assert abs(np.median(result_median.data)) < 1e-10
    print("  PASS\n")


# =========================================================================
# Analysis (non-FFT)
# =========================================================================

def test_statistics():
    print("=== Test: StatisticsNode ===")
    from backend.nodes.analysis import StatisticsNode
    node = StatisticsNode()

    data = np.array([[1, 2], [3, 4]], dtype=np.float64)
    field = make_field(data=data)

    table, = node.process(field)
    stats = {row["quantity"]: row["value"] for row in table}

    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
    assert stats["mean"] == 2.5
    assert stats["median"] == 2.5
    assert stats["range"] == 3.0
    # RMS = sqrt(mean((x - mean)^2))
    expected_rms = np.sqrt(np.mean((data - 2.5) ** 2))
    assert abs(stats["RMS"] - expected_rms) < 1e-10

    # Constant data should have RMS=0, skewness=0, kurtosis=0
    const_field = make_field(data=np.ones((4, 4)) * 5.0)
    table_const, = node.process(const_field)
    const_stats = {row["quantity"]: row["value"] for row in table_const}
    assert const_stats["RMS"] == 0.0
    assert const_stats["skewness"] == 0.0
    assert const_stats["kurtosis"] == 0.0
    print("  PASS\n")


def test_height_histogram():
    print("=== Test: HeightHistogram ===")
    from backend.nodes.analysis import HeightHistogram
    node = HeightHistogram()

    # Uniform data should give a roughly flat histogram
    data = np.linspace(0, 1, 1000).reshape(25, 40)
    field = make_field(data=data)

    counts, bin_centers = node.process(field, n_bins=10, y_scale="linear")
    assert len(counts) == 10
    assert len(bin_centers) == 10
    assert counts.dtype == np.float64
    # Total counts should equal number of pixels
    assert counts.sum() == 1000
    # For uniform data, each bin should have ~100 counts
    assert np.std(counts) < 10, f"Histogram not flat enough: std={np.std(counts)}"
    # Bin centers should span the data range
    assert bin_centers[0] > 0.0
    assert bin_centers[-1] < 1.0
    print("  PASS\n")


def test_cross_section():
    print("=== Test: CrossSection ===")
    from backend.nodes.analysis import CrossSection
    node = CrossSection()

    # Create a field with a known horizontal gradient
    N = 100
    y, x = np.mgrid[0:N, 0:N] / N
    data = x * 10.0  # value = 10 * x_fraction
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # Horizontal cross section at y=0.5
    (profile,) = node.process(
        field, x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        extend="none", n_samples=100,
    )
    assert len(profile) == 100
    # Profile should be a linear ramp from ~0 to ~10
    assert profile[0] < 0.5, f"Start of profile: {profile[0]}"
    assert profile[-1] > 9.5, f"End of profile: {profile[-1]}"

    # n_samples=0 should auto-calculate
    (profile_auto,) = node.process(
        field, x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        extend="none", n_samples=0,
    )
    assert len(profile_auto) >= 2

    # Test extend to edges — a short segment should be extended
    (profile_ext,) = node.process(
        field, x1=0.3, y1=0.5, x2=0.7, y2=0.5,
        extend="to_edges", n_samples=100,
    )
    # Extended profile should start near 0 and end near 10
    assert profile_ext[0] < 0.5
    assert profile_ext[-1] > 9.5

    # Diagonal cross section
    (profile_diag,) = node.process(
        field, x1=0.0, y1=0.0, x2=1.0, y2=1.0,
        extend="none", n_samples=50,
    )
    assert len(profile_diag) == 50
    print("  PASS\n")


# =========================================================================
# Grains
# =========================================================================

def test_threshold_mask():
    print("=== Test: ThresholdMask ===")
    from backend.nodes.mask import ThresholdMask
    node = ThresholdMask()

    # Clear bimodal data: left half = 0, right half = 1
    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)

    # Capture overlay preview
    previews = []
    ThresholdMask._broadcast_fn = lambda nid, uri: previews.append(uri)
    ThresholdMask._current_node_id = "test"

    # Absolute threshold at 0.5
    mask, = node.process(field, method="absolute", threshold=0.5, direction="above")
    assert mask.dtype == np.uint8
    assert mask.shape == (64, 64)
    assert np.all(mask[:, :32] == 0)
    assert np.all(mask[:, 32:] == 255)

    # Verify overlay preview was broadcast
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")

    # Direction "below"
    mask_below, = node.process(field, method="absolute", threshold=0.5, direction="below")
    assert np.all(mask_below[:, :32] == 255)
    assert np.all(mask_below[:, 32:] == 0)

    # Relative threshold at 0.5 (midpoint of range)
    mask_rel, = node.process(field, method="relative", threshold=0.5, direction="above")
    assert np.all(mask_rel[:, 32:] == 255)

    # Otsu should find the bimodal threshold
    mask_otsu, = node.process(field, method="otsu", threshold=0.0, direction="above")
    assert mask_otsu[:, 32:].sum() > mask_otsu[:, :32].sum()

    ThresholdMask._broadcast_fn = None
    print("  PASS\n")


def test_mask_morphology():
    print("=== Test: MaskMorphology ===")
    from backend.nodes.mask import MaskMorphology
    node = MaskMorphology()

    # Small square blob in the centre
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[28:36, 28:36] = 255  # 8x8 block
    orig_count = np.count_nonzero(mask)

    # Dilate should grow the region
    dilated, = node.process(mask, operation="dilate", radius=1, shape="square")
    assert dilated.dtype == np.uint8
    assert np.count_nonzero(dilated) > orig_count

    # Erode should shrink it
    eroded, = node.process(mask, operation="erode", radius=1, shape="square")
    assert np.count_nonzero(eroded) < orig_count

    # Open on a clean block should give back roughly the same block
    opened, = node.process(mask, operation="open", radius=1, shape="square")
    assert np.count_nonzero(opened) <= orig_count

    # Close on a mask with a 1-pixel hole should fill the hole
    mask_hole = mask.copy()
    mask_hole[32, 32] = 0  # poke a hole
    assert np.count_nonzero(mask_hole) == orig_count - 1
    closed, = node.process(mask_hole, operation="close", radius=1, shape="square")
    assert closed[32, 32] == 255, "Close should fill the 1-pixel hole"

    # Disk structuring element should also work
    dilated_disk, = node.process(mask, operation="dilate", radius=2, shape="disk")
    assert np.count_nonzero(dilated_disk) > orig_count

    print("  PASS\n")


def test_mask_invert():
    print("=== Test: MaskInvert ===")
    from backend.nodes.mask import MaskInvert
    node = MaskInvert()

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:20, 10:20] = 255

    inverted, = node.process(mask)
    assert inverted.dtype == np.uint8
    assert np.all(inverted[10:20, 10:20] == 0)
    assert np.all(inverted[0:10, 0:10] == 255)
    # Double-invert should return to original
    double, = node.process(inverted)
    assert np.array_equal(double, mask)

    print("  PASS\n")


def test_mask_combine():
    print("=== Test: MaskCombine ===")
    from backend.nodes.mask import MaskCombine
    node = MaskCombine()

    # Two overlapping squares
    a = np.zeros((64, 64), dtype=np.uint8)
    a[10:30, 10:30] = 255  # 20x20
    b = np.zeros((64, 64), dtype=np.uint8)
    b[20:40, 20:40] = 255  # 20x20, overlaps 10x10

    # AND — only the overlap
    result_and, = node.process(a, b, operation="and")
    assert np.all(result_and[20:30, 20:30] == 255)
    assert result_and[15, 15] == 0  # a-only region
    assert result_and[35, 35] == 0  # b-only region

    # OR — union
    result_or, = node.process(a, b, operation="or")
    assert result_or[15, 15] == 255
    assert result_or[35, 35] == 255
    assert result_or[25, 25] == 255
    assert result_or[5, 5] == 0

    # XOR — symmetric difference
    result_xor, = node.process(a, b, operation="xor")
    assert result_xor[15, 15] == 255  # a-only
    assert result_xor[35, 35] == 255  # b-only
    assert result_xor[25, 25] == 0    # overlap excluded

    # Subtract — a minus b
    result_sub, = node.process(a, b, operation="subtract")
    assert result_sub[15, 15] == 255  # a-only kept
    assert result_sub[25, 25] == 0    # overlap removed
    assert result_sub[35, 35] == 0    # b-only not included

    print("  PASS\n")


def test_particle_analysis():
    print("=== Test: ParticleAnalysis ===")
    from backend.nodes.grains import ParticleAnalysis
    node = ParticleAnalysis()

    # Create a field with two distinct particles
    N = 64
    data = np.zeros((N, N))
    # Particle 1: 10x10 block at top-left with height 5
    data[5:15, 5:15] = 5.0
    # Particle 2: 8x8 block at bottom-right with height 3
    data[45:53, 45:53] = 3.0
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # Create matching mask
    mask = np.zeros((N, N), dtype=np.uint8)
    mask[5:15, 5:15] = 255
    mask[45:53, 45:53] = 255

    table, = node.process(field, mask=mask, min_size=10)
    assert len(table) == 2, f"Expected 2 particles, got {len(table)}"

    # Sort by area descending
    table.sort(key=lambda r: r["area_px"], reverse=True)
    assert table[0]["area_px"] == 100  # 10x10
    assert table[1]["area_px"] == 64   # 8x8
    assert abs(table[0]["mean_height"] - 5.0) < 1e-10
    assert abs(table[1]["mean_height"] - 3.0) < 1e-10

    # min_size filtering: only keep particles >= 80 px
    table_filtered, = node.process(field, mask=mask, min_size=80)
    assert len(table_filtered) == 1
    assert table_filtered[0]["area_px"] == 100
    print("  PASS\n")


# =========================================================================
# I/O
# =========================================================================

def test_load_file():
    print("=== Test: LoadFile ===")
    from backend.nodes.io import LoadFile
    from PIL import Image
    node = LoadFile()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test loading a grayscale PNG → single DataField output
        arr = np.random.default_rng(1).integers(0, 256, (48, 64), dtype=np.uint8)
        img = Image.fromarray(arr, mode="L")
        path = os.path.join(tmpdir, "test_gray.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 1
        field = result[0]
        assert field.data.shape == (48, 64)
        assert field.data.dtype == np.float64

        # Test loading an RGB PNG (should average to grayscale)
        arr_rgb = np.random.default_rng(2).integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img_rgb = Image.fromarray(arr_rgb, mode="RGB")
        path_rgb = os.path.join(tmpdir, "test_rgb.png")
        img_rgb.save(path_rgb)

        result_rgb = node.load(filename=path_rgb)
        assert len(result_rgb) == 1
        assert result_rgb[0].data.shape == (32, 32)

        # Test loading a .npy file
        data_npy = np.random.default_rng(3).standard_normal((50, 60))
        path_npy = os.path.join(tmpdir, "test.npy")
        np.save(path_npy, data_npy)

        result_npy = node.load(filename=path_npy)
        assert np.allclose(result_npy[0].data, data_npy)

    print("  PASS\n")


def test_save_image():
    print("=== Test: SaveImage ===")
    from backend.nodes.io import SaveImage
    node = SaveImage()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Monkey-patch OUTPUT_DIR for testing
        from pathlib import Path
        import backend.nodes.io as io_mod
        orig_dir = io_mod.OUTPUT_DIR
        io_mod.OUTPUT_DIR = Path(tmpdir)

        try:
            arr = np.random.default_rng(4).integers(0, 256, (32, 32), dtype=np.uint8)

            # Save as PNG
            node.save(image=arr, filename_prefix="test", format="PNG")
            saved = os.listdir(tmpdir)
            assert any(f.endswith(".png") for f in saved), f"No PNG file found in {saved}"

            # Save as NPY
            node.save(image=arr.astype(np.float64), filename_prefix="test", format="NPY")
            saved = os.listdir(tmpdir)
            assert any(f.endswith(".npy") for f in saved), f"No NPY file found in {saved}"
        finally:
            io_mod.OUTPUT_DIR = orig_dir

    print("  PASS\n")


# =========================================================================
# Display (limited testing — these are output nodes with WS callbacks)
# =========================================================================

def test_preview_image():
    print("=== Test: PreviewImage ===")
    from backend.nodes.display import PreviewImage
    node = PreviewImage()

    # Set up a capture for the broadcast
    captured = []
    PreviewImage._broadcast_fn = lambda node_id, data_uri: captured.append(data_uri)
    PreviewImage._current_node_id = "test"

    # Preview with a DataField
    field = make_field()
    node.preview(colormap="viridis", field=field)
    assert len(captured) == 1
    assert captured[0].startswith("data:image/png;base64,")

    # Preview with an IMAGE array
    captured.clear()
    arr = np.random.default_rng(5).integers(0, 256, (32, 32), dtype=np.uint8)
    node.preview(colormap="gray", image=arr)
    assert len(captured) == 1

    # Clean up
    PreviewImage._broadcast_fn = None
    print("  PASS\n")


def test_print_table():
    print("=== Test: PrintTable ===")
    from backend.nodes.display import PrintTable
    node = PrintTable()

    captured = []
    PrintTable._broadcast_table_fn = lambda node_id, rows: captured.append(rows)
    PrintTable._current_node_id = "test"

    table = [{"quantity": "test", "value": 42.0, "unit": "m"}]
    node.print_table(table=table)
    assert len(captured) == 1
    assert captured[0] == table

    PrintTable._broadcast_table_fn = None
    print("  PASS\n")


# =========================================================================
# I/O — IBW multi-channel loading
# =========================================================================

def test_load_file_ibw():
    print("=== Test: LoadFile IBW multi-channel ===")
    from backend.nodes.io import LoadFile

    node = LoadFile()
    ibw_path = os.path.join(os.path.dirname(__file__), "..", "demo", "BR_New20012.ibw")
    ibw_path = os.path.abspath(ibw_path)
    if not os.path.exists(ibw_path):
        print("  SKIP (demo IBW file not found)\n")
        return

    result = node.load(filename=ibw_path)

    # BR_New20012.ibw has 4 channels
    assert len(result) == 4, f"Expected 4 channels, got {len(result)}"

    for i, field in enumerate(result):
        assert isinstance(field, DataField), f"Channel {i} is not a DataField"
        assert field.data.shape == (512, 1024), f"Channel {i} shape: {field.data.shape}"
        assert field.data.dtype == np.float64
        # Physical dimensions should be populated (not default 1e-6)
        assert field.xreal > 1e-8, f"Channel {i} xreal too small: {field.xreal}"
        assert field.yreal > 1e-8, f"Channel {i} yreal too small: {field.yreal}"
        assert field.si_unit_xy == "m"
        assert field.si_unit_z == "m"

    # All channels should share the same physical dimensions
    assert result[0].xreal == result[1].xreal
    assert result[0].yreal == result[1].yreal

    # Different channels should have different data
    assert not np.array_equal(result[0].data, result[1].data)

    print("  PASS\n")


def test_load_file_npz():
    print("=== Test: LoadFile .npz ===")
    from backend.nodes.io import LoadFile

    node = LoadFile()
    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.random.default_rng(99).standard_normal((30, 40))
        path = os.path.join(tmpdir, "test.npz")
        np.savez(path, my_array=data)

        result = node.load(filename=path)
        assert len(result) == 1
        assert np.allclose(result[0].data, data)

    print("  PASS\n")


def test_load_file_not_found():
    print("=== Test: LoadFile not found ===")
    from backend.nodes.io import LoadFile

    node = LoadFile()
    try:
        node.load(filename="/nonexistent/path/file.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass

    print("  PASS\n")


def test_load_file_unsupported():
    print("=== Test: LoadFile unsupported format ===")
    from backend.nodes.io import LoadFile

    node = LoadFile()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.xyz")
        with open(path, "w") as f:
            f.write("hello")
        try:
            node.load(filename=path)
            assert False, "Should have raised an error for .xyz"
        except Exception:
            pass

    print("  PASS\n")


def test_load_file_warning():
    print("=== Test: LoadFile warning for uncalibrated data ===")
    from backend.nodes.io import LoadFile
    from PIL import Image

    node = LoadFile()
    warnings = []
    LoadFile._broadcast_warning_fn = lambda nid, msg: warnings.append(msg)
    LoadFile._current_node_id = "test"

    with tempfile.TemporaryDirectory() as tmpdir:
        arr = np.random.default_rng(10).integers(0, 256, (16, 16), dtype=np.uint8)
        img = Image.fromarray(arr)
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 1
        assert len(warnings) == 1
        assert "Uncalibrated" in warnings[0]

    LoadFile._broadcast_warning_fn = None
    print("  PASS\n")


# =========================================================================
# I/O — list_channels helper
# =========================================================================

def test_list_channels():
    print("=== Test: list_channels ===")
    from backend.nodes.io import list_channels

    # Non-existent file → default
    ch = list_channels("/nonexistent/file.ibw")
    assert len(ch) == 1
    assert ch[0]["name"] == "field"

    # IBW with channels
    ibw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo", "BR_New20012.ibw"))
    if os.path.exists(ibw_path):
        ch = list_channels(ibw_path)
        assert len(ch) == 4
        names = [c["name"] for c in ch]
        assert "HeightRetrace" in names
        assert "AmplitudeRetrace" in names
        assert all(c["type"] == "DATA_FIELD" for c in ch)

    # Plain image → single default channel
    with tempfile.TemporaryDirectory() as tmpdir:
        from PIL import Image
        img = Image.fromarray(np.zeros((8, 8), dtype=np.uint8))
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        ch = list_channels(path)
        assert len(ch) == 1
        assert ch[0]["name"] == "field"

    # .npy → single default channel
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.npy")
        np.save(path, np.zeros((4, 4)))

        ch = list_channels(path)
        assert len(ch) == 1

    print("  PASS\n")


# =========================================================================
# I/O — LoadDemo
# =========================================================================

def test_load_demo():
    print("=== Test: LoadDemo ===")
    from backend.nodes.io import LoadDemo

    node = LoadDemo()

    # Should be able to load a demo file by name
    result = node.load(name="nanoparticles.npy")
    assert len(result) >= 1
    assert isinstance(result[0], DataField)
    assert result[0].data.ndim == 2

    # IBW demo should return multiple channels
    result_ibw = node.load(name="whiskers.ibw")
    assert len(result_ibw) == 4
    for field in result_ibw:
        assert isinstance(field, DataField)

    # Non-existent demo should raise
    try:
        node.load(name="nonexistent_file.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass

    print("  PASS\n")


# =========================================================================
# I/O — Coordinate
# =========================================================================

def test_coordinate():
    print("=== Test: Coordinate ===")
    from backend.nodes.io import Coordinate

    node = Coordinate()

    result = node.process(x=0.3, y=0.7)
    assert len(result) == 1
    assert result[0] == (0.3, 0.7)

    # Edge values
    result_zero = node.process(x=0.0, y=0.0)
    assert result_zero[0] == (0.0, 0.0)

    result_one = node.process(x=1.0, y=1.0)
    assert result_one[0] == (1.0, 1.0)

    print("  PASS\n")


# =========================================================================
# Analysis — LineCursors
# =========================================================================

def test_line_cursors():
    print("=== Test: LineCursors ===")
    from backend.nodes.analysis import LineCursors

    node = LineCursors()

    # Create a simple linear ramp
    line = np.linspace(0, 10, 100).astype(np.float64)

    # Capture overlay
    overlays = []
    LineCursors._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    LineCursors._current_node_id = "test"

    table, = node.process(line, x1=0.25, y1=0.5, x2=0.75, y2=0.5)

    # Should produce a 6-row table
    assert len(table) == 6
    quantities = {row["quantity"] for row in table}
    assert "A position" in quantities
    assert "B position" in quantities
    assert "delta X" in quantities
    assert "delta Y" in quantities

    # B should be at a later position than A
    a_pos = next(r["value"] for r in table if r["quantity"] == "A position")
    b_pos = next(r["value"] for r in table if r["quantity"] == "B position")
    assert b_pos > a_pos

    # Delta Y should reflect the height difference along the ramp
    dy = next(r["value"] for r in table if r["quantity"] == "delta Y")
    assert dy > 0  # ramp goes upward

    # Overlay should have been broadcast
    assert len(overlays) == 1
    assert "image" in overlays[0]
    assert overlays[0]["image"].startswith("data:image/png;base64,")

    # With x_axis provided
    x_axis = np.linspace(0, 1, 100).astype(np.float64)
    table2, = node.process(line, x1=0.25, y1=0.5, x2=0.75, y2=0.5, x_axis=x_axis)
    assert len(table2) == 6

    LineCursors._broadcast_overlay_fn = None
    print("  PASS\n")


# =========================================================================
# Analysis — FFT2D
# =========================================================================

def test_fft2d():
    print("=== Test: FFT2D ===")
    from backend.nodes.analysis import FFT2D

    node = FFT2D()

    # Pure single-frequency signal: peak should appear at the right location
    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    freq = 5
    data = np.sin(2 * np.pi * freq * x)
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # log_magnitude
    spectrum, = node.process(field, windowing="none", level="none", output="log_magnitude")
    assert spectrum.data.shape == (N, N)
    assert spectrum.domain == "frequency"
    assert spectrum.si_unit_xy == "1/m"
    # Peak should be symmetric about centre
    centre = N // 2
    row = spectrum.data[centre, :]
    peak_idx = np.argmax(row[centre + 1:]) + centre + 1
    assert abs(peak_idx - (centre + freq)) <= 1, f"Peak at {peak_idx}, expected ~{centre + freq}"

    # magnitude output
    spec_mag, = node.process(field, windowing="hann", level="mean", output="magnitude")
    assert spec_mag.data.shape == (N, N)
    assert np.all(spec_mag.data >= 0)

    # phase output
    spec_phase, = node.process(field, windowing="none", level="none", output="phase")
    assert spec_phase.data.shape == (N, N)
    assert spec_phase.data.min() >= -np.pi - 0.01
    assert spec_phase.data.max() <= np.pi + 0.01

    # psdf output — units should reflect PSDF calibration
    spec_psdf, = node.process(field, windowing="hamming", level="plane", output="psdf")
    assert spec_psdf.data.shape == (N, N)
    assert np.all(spec_psdf.data >= 0)
    assert "^2" in spec_psdf.si_unit_z

    # Constant field should have all energy at DC
    const_field = make_field(data=np.ones((32, 32)) * 3.0)
    spec_const, = node.process(const_field, windowing="none", level="none", output="magnitude")
    centre32 = 16
    dc_val = spec_const.data[centre32, centre32]
    assert dc_val == spec_const.data.max(), "DC should be the maximum for constant field"

    # Blackman windowing should also work without error
    spec_bk, = node.process(field, windowing="blackman", level="none", output="log_magnitude")
    assert spec_bk.data.shape == (N, N)

    print("  PASS\n")


# =========================================================================
# Analysis — LineMath
# =========================================================================

def test_line_math():
    print("=== Test: LineMath ===")
    from backend.nodes.analysis import LineMath

    node = LineMath()
    line = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    # Basic stats
    table, = node.process(line, operation="min")
    assert table[0]["value"] == 1.0

    table, = node.process(line, operation="max")
    assert table[0]["value"] == 5.0

    table, = node.process(line, operation="mean")
    assert table[0]["value"] == 3.0

    table, = node.process(line, operation="median")
    assert table[0]["value"] == 3.0

    table, = node.process(line, operation="sum")
    assert table[0]["value"] == 15.0

    table, = node.process(line, operation="range")
    assert table[0]["value"] == 4.0

    table, = node.process(line, operation="length")
    assert table[0]["value"] == 5.0

    # RMS of [1,2,3,4,5]
    table, = node.process(line, operation="rms")
    expected_rms = np.sqrt(np.mean(line ** 2))
    assert abs(table[0]["value"] - expected_rms) < 1e-10

    # Roughness parameters
    table, = node.process(line, operation="Ra")
    d = line - line.mean()
    expected_ra = float(np.mean(np.abs(d)))
    assert abs(table[0]["value"] - expected_ra) < 1e-10

    table, = node.process(line, operation="Rq")
    expected_rq = float(np.sqrt(np.mean(d ** 2)))
    assert abs(table[0]["value"] - expected_rq) < 1e-10

    # Rp = max of (z - mean)
    table, = node.process(line, operation="Rp")
    assert abs(table[0]["value"] - d.max()) < 1e-10

    # Rv = -(min of (z - mean))
    table, = node.process(line, operation="Rv")
    assert abs(table[0]["value"] - (-d.min())) < 1e-10

    # Rt = Rp + Rv = range of (z - mean)
    table, = node.process(line, operation="Rt")
    assert abs(table[0]["value"] - (d.max() - d.min())) < 1e-10

    # Constant line: roughness parameters should all be zero
    const_line = np.ones(10) * 7.0
    table, = node.process(const_line, operation="Ra")
    assert table[0]["value"] == 0.0
    table, = node.process(const_line, operation="Rq")
    assert table[0]["value"] == 0.0
    table, = node.process(const_line, operation="Rsk")
    assert table[0]["value"] == 0.0
    table, = node.process(const_line, operation="Rku")
    assert table[0]["value"] == 0.0

    # Slope-based: Dq and Da
    table, = node.process(line, operation="Dq")
    dz = np.diff(line)
    expected_dq = float(np.sqrt(np.mean(dz * dz)))
    assert abs(table[0]["value"] - expected_dq) < 1e-10

    table, = node.process(line, operation="Da")
    expected_da = float(np.mean(np.abs(dz)))
    assert abs(table[0]["value"] - expected_da) < 1e-10

    print("  PASS\n")


# =========================================================================
# Display — View3D
# =========================================================================

def test_view3d():
    print("=== Test: View3D ===")
    from backend.nodes.display import View3D

    node = View3D()
    field = make_field()

    captured = []
    View3D._broadcast_mesh_fn = lambda nid, mesh: captured.append(mesh)
    View3D._current_node_id = "test"

    result = node.render(field, colormap="viridis", z_scale=2.0, resolution=64)
    assert result == ()
    assert len(captured) == 1

    mesh = captured[0]
    assert "width" in mesh
    assert "height" in mesh
    assert "z_data" in mesh
    assert "colors" in mesh
    assert mesh["z_scale"] == 2.0
    assert mesh["width"] <= 64
    assert mesh["height"] <= 64
    # z_min < z_max for non-constant data
    assert mesh["z_min"] < mesh["z_max"]

    # Verify base64 data can be decoded
    import base64
    z_bytes = base64.b64decode(mesh["z_data"])
    assert len(z_bytes) == mesh["width"] * mesh["height"] * 4  # float32

    colors_bytes = base64.b64decode(mesh["colors"])
    assert len(colors_bytes) == mesh["width"] * mesh["height"] * 3  # uint8 RGB

    # High-res input should be downsampled
    big_field = make_field(shape=(256, 256))
    captured.clear()
    node.render(big_field, colormap="hot", z_scale=1.0, resolution=64)
    assert captured[0]["width"] <= 64
    assert captured[0]["height"] <= 64

    View3D._broadcast_mesh_fn = None
    print("  PASS\n")


# =========================================================================
# Run all tests
# =========================================================================

if __name__ == "__main__":
    # Filters
    test_gaussian_filter()
    test_median_filter()
    test_edge_detect()
    test_fft_filter_1d()
    test_fft_filter_2d()

    # Level
    test_plane_level()
    test_poly_level()
    test_fix_zero()

    # Analysis
    test_statistics()
    test_height_histogram()
    test_cross_section()
    test_line_cursors()
    test_fft2d()
    test_line_math()

    # Mask
    test_threshold_mask()
    test_mask_morphology()
    test_mask_invert()
    test_mask_combine()

    # Grains
    test_particle_analysis()

    # I/O
    test_load_file()
    test_load_file_ibw()
    test_load_file_npz()
    test_load_file_not_found()
    test_load_file_unsupported()
    test_load_file_warning()
    test_list_channels()
    test_load_demo()
    test_coordinate()
    test_save_image()

    # Display
    test_preview_image()
    test_print_table()
    test_view3d()

    print("All tests passed!")
