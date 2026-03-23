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

    counts, bin_centers = node.process(field, n_bins=10)
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
    from backend.nodes.grains import ThresholdMask
    node = ThresholdMask()

    # Clear bimodal data: left half = 0, right half = 1
    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)

    # Absolute threshold at 0.5
    mask, = node.process(field, method="absolute", threshold=0.5, direction="above")
    assert mask.dtype == np.uint8
    assert mask.shape == (64, 64)
    assert np.all(mask[:, :32] == 0)
    assert np.all(mask[:, 32:] == 255)

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
    print("  PASS\n")


def test_grain_analysis():
    print("=== Test: GrainAnalysis ===")
    from backend.nodes.grains import GrainAnalysis
    node = GrainAnalysis()

    # Create a field with two distinct "grains"
    N = 64
    data = np.zeros((N, N))
    # Grain 1: 10x10 block at top-left with height 5
    data[5:15, 5:15] = 5.0
    # Grain 2: 8x8 block at bottom-right with height 3
    data[45:53, 45:53] = 3.0
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # Create matching mask
    mask = np.zeros((N, N), dtype=np.uint8)
    mask[5:15, 5:15] = 255
    mask[45:53, 45:53] = 255

    table, = node.process(field, mask=mask, min_size=10)
    assert len(table) == 2, f"Expected 2 grains, got {len(table)}"

    # Sort by area descending
    table.sort(key=lambda r: r["area_px"], reverse=True)
    assert table[0]["area_px"] == 100  # 10x10
    assert table[1]["area_px"] == 64   # 8x8
    assert abs(table[0]["mean_height"] - 5.0) < 1e-10
    assert abs(table[1]["mean_height"] - 3.0) < 1e-10

    # min_size filtering: only keep grains >= 80 px
    table_filtered, = node.process(field, mask=mask, min_size=80)
    assert len(table_filtered) == 1
    assert table_filtered[0]["area_px"] == 100
    print("  PASS\n")


# =========================================================================
# I/O
# =========================================================================

def test_load_image():
    print("=== Test: LoadImage ===")
    from backend.nodes.io import LoadImage
    from PIL import Image
    node = LoadImage()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test loading a grayscale PNG
        arr = np.random.default_rng(1).integers(0, 256, (48, 64), dtype=np.uint8)
        img = Image.fromarray(arr, mode="L")
        path = os.path.join(tmpdir, "test_gray.png")
        img.save(path)

        image, field = node.load(filename=path)
        assert image.shape == (48, 64)
        assert field.data.shape == (48, 64)
        assert field.data.dtype == np.float64

        # Test loading an RGB PNG (should average to grayscale for field)
        arr_rgb = np.random.default_rng(2).integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img_rgb = Image.fromarray(arr_rgb, mode="RGB")
        path_rgb = os.path.join(tmpdir, "test_rgb.png")
        img_rgb.save(path_rgb)

        image_rgb, field_rgb = node.load(filename=path_rgb)
        assert image_rgb.shape == (32, 32, 3)
        assert field_rgb.data.shape == (32, 32)

        # Test loading a .npy file
        data_npy = np.random.default_rng(3).standard_normal((50, 60))
        path_npy = os.path.join(tmpdir, "test.npy")
        np.save(path_npy, data_npy)

        image_npy, field_npy = node.load(filename=path_npy)
        assert np.allclose(field_npy.data, data_npy)

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
# Run all tests
# =========================================================================

if __name__ == "__main__":
    # Filters
    test_gaussian_filter()
    test_median_filter()
    test_edge_detect()

    # Level
    test_plane_level()
    test_poly_level()
    test_fix_zero()

    # Analysis
    test_statistics()
    test_height_histogram()
    test_cross_section()

    # Grains
    test_threshold_mask()
    test_grain_analysis()

    # I/O
    test_load_image()
    test_save_image()

    # Display
    test_preview_image()
    test_print_table()

    print("All tests passed!")
