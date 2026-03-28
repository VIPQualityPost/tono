"""
Tests for all argonode backend nodes (excluding FFT2D which has its own test file).

Run from project root:
    .venv/bin/python -m tests.test_nodes
"""
import json
import sys
import os
import tempfile
from pathlib import Path
import numpy as np

sys.path.insert(0, ".")
from backend.data_types import DataField, LineData, MeasureTable, RecordTable, datafield_to_uint8, render_datafield_preview


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
    from backend.nodes.gaussian_filter import GaussianFilter
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
    from backend.nodes.median_filter import MedianFilter
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


def test_crop_resize_field():
    print("=== Test: CropResizeField ===")
    from backend.nodes.crop_resize_field import CropResizeField
    node = CropResizeField()

    data = np.arange(32, dtype=np.float64).reshape(4, 8)
    field = DataField(
        data=data,
        xreal=8.0,
        yreal=4.0,
        xoff=10.0,
        yoff=20.0,
        si_unit_xy="nm",
        si_unit_z="nm",
        overlays=[{"kind": "markup", "shapes": [{"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 2, "color": "#ffffff"}]}],
    )

    overlays = []
    CropResizeField._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    CropResizeField._current_node_id = "test"

    cropped, = node.process(
        field,
        x1=0.25,
        y1=0.25,
        x2=0.75,
        y2=1.0,
        target_width=0,
        target_height=0,
        interpolation="bilinear",
    )
    assert cropped.data.shape == (3, 4)
    assert np.array_equal(cropped.data, data[1:4, 2:6])
    assert cropped.xreal == 4.0
    assert cropped.yreal == 3.0
    assert cropped.xoff == 12.0
    assert cropped.yoff == 21.0
    assert cropped.si_unit_xy == field.si_unit_xy
    assert cropped.si_unit_z == field.si_unit_z
    assert cropped.overlays == []
    assert len(overlays) == 1
    assert overlays[0]["kind"] == "crop_box"
    assert overlays[0]["image"].startswith("data:image/png;base64,")
    assert overlays[0]["a_locked"] is False
    assert overlays[0]["b_locked"] is False

    resized, = node.process(
        field,
        x1=0.0,
        y1=0.0,
        x2=1.0,
        y2=1.0,
        target_width=8,
        target_height=0,
        interpolation="bilinear",
        corner_a=(0.25, 0.25),
        corner_b=(0.75, 1.0),
    )
    assert resized.data.shape == (6, 8)
    assert resized.xreal == cropped.xreal
    assert resized.yreal == cropped.yreal
    assert resized.xoff == cropped.xoff
    assert resized.yoff == cropped.yoff
    assert resized.domain == field.domain
    assert overlays[-1]["a_locked"] is True
    assert overlays[-1]["b_locked"] is True

    reversed_crop, = node.process(
        field,
        x1=0.75,
        y1=1.0,
        x2=0.25,
        y2=0.25,
        target_width=0,
        target_height=0,
        interpolation="nearest",
    )
    assert np.array_equal(reversed_crop.data, cropped.data)

    try:
        node.process(
            field,
            x1=0.9,
            y1=0.0,
            x2=0.9,
            y2=1.0,
            target_width=0,
            target_height=0,
            interpolation="nearest",
        )
        raise AssertionError("Expected invalid crop bounds to raise ValueError")
    except ValueError:
        pass

    CropResizeField._broadcast_overlay_fn = None

    print("  PASS\n")


def test_rotate_field():
    print("=== Test: RotateField ===")
    from backend.nodes.rotate_field import RotateField
    node = RotateField()

    data = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64)
    field = DataField(
        data=data,
        xreal=6.0,
        yreal=4.0,
        xoff=10.0,
        yoff=20.0,
        si_unit_xy="nm",
        si_unit_z="nm",
    )

    rotated_90, = node.process(
        field,
        angle=90.0,
        interpolation="nearest",
        expand_canvas=True,
    )
    assert np.array_equal(rotated_90.data, np.rot90(data))
    assert rotated_90.data.shape == (3, 2)
    assert rotated_90.xreal == 4.0
    assert rotated_90.yreal == 6.0
    assert rotated_90.xoff == 11.0
    assert rotated_90.yoff == 19.0
    assert rotated_90.si_unit_xy == field.si_unit_xy
    assert rotated_90.si_unit_z == field.si_unit_z
    assert rotated_90.overlays == []

    rotated_180, = node.process(
        field,
        angle=180.0,
        interpolation="nearest",
        expand_canvas=False,
    )
    assert np.array_equal(rotated_180.data, np.rot90(data, 2))
    assert rotated_180.data.shape == data.shape
    assert rotated_180.xreal == field.xreal
    assert rotated_180.yreal == field.yreal
    assert rotated_180.xoff == field.xoff
    assert rotated_180.yoff == field.yoff

    rotated_45, = node.process(
        field,
        angle=45.0,
        interpolation="bilinear",
        expand_canvas=True,
    )
    expected_xreal = abs(field.xreal * np.cos(np.deg2rad(45.0))) + abs(field.yreal * np.sin(np.deg2rad(45.0)))
    expected_yreal = abs(field.xreal * np.sin(np.deg2rad(45.0))) + abs(field.yreal * np.cos(np.deg2rad(45.0)))
    assert rotated_45.data.shape[0] > field.data.shape[0]
    assert rotated_45.data.shape[1] > field.data.shape[1]
    assert np.isclose(rotated_45.xreal, expected_xreal)
    assert np.isclose(rotated_45.yreal, expected_yreal)
    assert np.isclose(rotated_45.xoff + rotated_45.xreal / 2.0, field.xoff + field.xreal / 2.0)
    assert np.isclose(rotated_45.yoff + rotated_45.yreal / 2.0, field.yoff + field.yreal / 2.0)

    print("  PASS\n")


def test_rotate_field_overlay_warning():
    print("=== Test: RotateField overlay warning ===")
    from backend.nodes.rotate_field import RotateField

    node = RotateField()
    warnings = []
    RotateField._broadcast_warning_fn = lambda nid, msg: warnings.append(msg)
    RotateField._current_node_id = "test"

    field = DataField(
        data=np.arange(16, dtype=np.float64).reshape(4, 4),
        overlays=[{"kind": "markup", "shapes": [{"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 2, "color": "#ffffff"}]}],
    )

    rotated, = node.process(
        field,
        angle=30.0,
        interpolation="bilinear",
        expand_canvas=True,
    )
    assert rotated.overlays == []
    assert len(warnings) == 1
    assert "clears annotation/markup overlays" in warnings[0]

    RotateField._broadcast_warning_fn = None
    print("  PASS\n")


def test_view3d_normalizes_small_physical_extents_for_display():
    print("=== Test: View3D extent normalization ===")
    from backend.nodes.view_3d import View3D

    data = np.linspace(0.0, 1.0, 64 * 64, dtype=np.float64).reshape(64, 64)
    field = DataField(
        data=data,
        xreal=1.0e-5,
        yreal=1.0e-5,
        si_unit_xy="m",
        si_unit_z="m",
    )

    node = View3D()
    mesh, _ = node.render(field, colormap="auto", z_scale=1.0, resolution=64, make_solid=False)

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    spans = vertices.max(axis=0) - vertices.min(axis=0)

    assert np.isclose(spans[0], 1.0, atol=1e-6)
    assert np.isclose(spans[2], 1.0, atol=1e-6)
    assert spans[1] > 0.09
    print("  PASS\n")


def test_colormap_adjust():
    print("=== Test: ColormapAdjust ===")
    from backend.nodes.colormap_adjust import ColormapAdjust

    node = ColormapAdjust()
    field = DataField(
        data=np.array([[0.0, 0.25, 0.5, 0.75, 1.0]], dtype=np.float64),
        xreal=5.0,
        yreal=1.0,
        colormap="gray",
    )

    adjusted, = node.process(field, offset=0.25, scale=0.5)
    assert np.array_equal(adjusted.data, field.data)
    assert adjusted.display_offset == 0.25
    assert adjusted.display_scale == 0.5
    assert adjusted.colormap == field.colormap

    rgb = datafield_to_uint8(adjusted, "gray")
    intensities = rgb[0, :, 0]
    assert intensities[0] == 0
    assert intensities[1] == 0
    assert 110 <= intensities[2] <= 145
    assert intensities[3] == 255
    assert intensities[4] == 255

    auto_like, = node.process(field, offset=0.0, scale=1.0)
    auto_rgb = datafield_to_uint8(auto_like, "gray")
    auto_intensities = auto_rgb[0, :, 0]
    assert auto_intensities[0] == 0
    assert auto_intensities[-1] == 255

    try:
        node.process(field, offset=0.0, scale=0.0)
        raise AssertionError("Expected non-positive scale to raise ValueError")
    except ValueError:
        pass

    print("  PASS\n")


def test_edge_detect():
    print("=== Test: EdgeDetect ===")
    from backend.nodes.edge_detect import EdgeDetect
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
    from backend.nodes.fft_filter_1d import FFTFilter1D
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
    from backend.nodes.fft_filter_2d import FFTFilter2D
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
    from backend.nodes.plane_level_field import PlaneLevelField
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
    from backend.nodes.poly_level_field import PolyLevelField
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
    from backend.nodes.fix_zero import FixZero
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
    print("=== Test: Statistics ===")
    from backend.nodes.statistics_node import Statistics
    node = Statistics()

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
    print("=== Test: Histogram ===")
    from backend.nodes.histogram import Histogram
    node = Histogram()

    # Uniform data should give a roughly flat histogram
    data = np.linspace(0, 1, 1000).reshape(25, 40)
    field = make_field(data=data)

    overlays = []
    Histogram._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    Histogram._current_node_id = "test"

    table, coord_pair = node.process(
        field,
        n_bins=10,
        y_scale="linear",
        x1=0.2,
        y1=0.5,
        x2=0.8,
        y2=0.5,
    )
    assert isinstance(coord_pair, tuple) and len(coord_pair) == 2
    measurements = {row["quantity"]: row for row in table}
    assert "A position" in measurements
    assert "A count" in measurements
    assert "B position" in measurements
    assert "B count" in measurements
    assert "delta X" in measurements
    assert "delta Y" in measurements
    assert measurements["A count"]["unit"] == "count"
    assert measurements["B count"]["unit"] == "count"
    assert measurements["B position"]["value"] > measurements["A position"]["value"]
    assert len(overlays) == 1
    assert overlays[0]["kind"] == "line_plot"
    assert overlays[0]["section_title"] == "Histogram"
    assert len(overlays[0]["line"]) == 10
    assert len(overlays[0]["x_axis"]) == 10
    assert np.isclose(overlays[0]["x1"], 0.2)
    assert np.isclose(overlays[0]["x2"], 0.8)
    assert np.isclose(
        measurements["delta Y"]["value"],
        measurements["B count"]["value"] - measurements["A count"]["value"],
    )

    Histogram._broadcast_overlay_fn = None
    print("  PASS\n")


def test_cross_section():
    print("=== Test: CrossSection ===")
    from backend.nodes.cross_section import CrossSection
    node = CrossSection()

    # Create a field with a known horizontal gradient
    N = 100
    y, x = np.mgrid[0:N, 0:N] / N
    data = x * 10.0  # value = 10 * x_fraction
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # Horizontal cross section at y=0.5
    profile, marker_pair = node.process(
        field, x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        extend="none", n_samples=100,
    )
    assert isinstance(marker_pair, tuple) and len(marker_pair) == 2
    assert isinstance(profile, LineData)
    assert len(profile) == 100
    assert profile.x_unit == field.si_unit_xy
    assert profile.y_unit == field.si_unit_z
    assert np.isclose(profile.x_axis[0], 0.0)
    assert np.isclose(profile.x_axis[-1], field.xreal)
    # Profile should be a linear ramp from ~0 to ~10
    assert profile[0] < 0.5, f"Start of profile: {profile[0]}"
    assert profile[-1] > 9.5, f"End of profile: {profile[-1]}"

    # n_samples=0 should auto-calculate
    profile_auto, _ = node.process(
        field, x1=0.0, y1=0.5, x2=1.0, y2=0.5,
        extend="none", n_samples=0,
    )
    assert len(profile_auto) >= 2

    # Test extend to edges — a short segment should be extended
    profile_ext, _ = node.process(
        field, x1=0.3, y1=0.5, x2=0.7, y2=0.5,
        extend="to_edges", n_samples=100,
    )
    # Extended profile should start near 0 and end near 10
    assert profile_ext[0] < 0.5
    assert profile_ext[-1] > 9.5

    # Diagonal cross section
    profile_diag, _ = node.process(
        field, x1=0.0, y1=0.0, x2=1.0, y2=1.0,
        extend="none", n_samples=50,
    )
    assert len(profile_diag) == 50

    from backend.nodes.cursors import Cursors
    from backend.nodes.stats import Stats

    cursors = Cursors()
    table, _ = cursors.process(profile, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
    rows = {row["quantity"]: row for row in table}
    assert rows["dx"]["unit"] == field.si_unit_xy
    assert rows["dy"]["unit"] == field.si_unit_z

    captured = []
    Stats._broadcast_value_fn = lambda nid, payload: captured.append(payload)
    Stats._current_node_id = "test"
    stats = Stats()
    mean_value, = stats.process(profile, operation="mean", column="value")
    assert mean_value > 0
    assert captured[-1]["unit"] == field.si_unit_z
    Stats._broadcast_value_fn = None

    print("  PASS\n")


# =========================================================================
# Grains
# =========================================================================

def test_threshold_mask():
    print("=== Test: ThresholdMask ===")
    from backend.nodes.threshold_mask import ThresholdMask
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
    from backend.nodes.mask_morphology import MaskMorphology
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
    from backend.nodes.mask_invert import MaskInvert
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
    from backend.nodes.mask_combine import MaskCombine
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


def test_draw_mask():
    print("=== Test: DrawMask ===")
    from backend.nodes.draw_mask import DrawMask
    node = DrawMask()

    field = make_field(data=np.zeros((32, 32), dtype=np.float64))
    overlays = []
    DrawMask._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    DrawMask._current_node_id = "test"

    mask_paths = [
        {
            "size": 5,
            "points": [
                {"x": 0.2, "y": 0.5},
                {"x": 0.8, "y": 0.5},
            ],
        }
    ]

    mask, = node.process(field, pen_size=2, invert=False, mask_paths=json.dumps(mask_paths))
    assert mask.dtype == np.uint8
    assert mask.shape == (32, 32)
    assert mask[16, 16] == 255
    assert mask[14, 16] == 255
    assert mask[0, 0] == 0

    assert len(overlays) == 1
    assert overlays[0]["kind"] == "mask_paint"
    assert overlays[0]["section_title"] == "Mask"
    assert overlays[0]["image"].startswith("data:image/png;base64,")
    assert overlays[0]["image_width"] == field.xres
    assert overlays[0]["image_height"] == field.yres
    assert overlays[0]["invert"] is False

    inverted, = node.process(field, pen_size=2, invert=True, mask_paths=json.dumps(mask_paths))
    assert inverted[16, 16] == 0
    assert inverted[0, 0] == 255
    assert overlays[-1]["invert"] is True

    cleared, = node.process(field, pen_size=12, invert=False, mask_paths="[]")
    assert np.count_nonzero(cleared) == 0

    DrawMask._broadcast_overlay_fn = None
    print("  PASS\n")


def test_particle_analysis():
    print("=== Test: ParticleAnalysis ===")
    from backend.nodes.particle_analysis import ParticleAnalysis
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
    print("=== Test: Image ===")
    from backend.nodes.image import Image as ImageNode
    from PIL import Image as PILImage
    node = ImageNode()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test loading a grayscale PNG → single DataField output
        arr = np.random.default_rng(1).integers(0, 256, (48, 64), dtype=np.uint8)
        img = PILImage.fromarray(arr, mode="L")
        path = os.path.join(tmpdir, "test_gray.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 1
        field = result[0]
        assert field.data.shape == (48, 64)
        assert field.data.dtype == np.float64

        # Test loading an RGB PNG (should average to grayscale)
        arr_rgb = np.random.default_rng(2).integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img_rgb = PILImage.fromarray(arr_rgb, mode="RGB")
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

        custom_colormap = {
            "mode": "custom",
            "stops": [
                {"position": 0.0, "color": "#000000"},
                {"position": 0.5, "color": "#ff0000"},
                {"position": 1.0, "color": "#ffffff"},
            ],
        }
        result_custom = node.load(filename=path, colormap_map=custom_colormap)
        assert isinstance(result_custom[0].colormap, dict)
        assert result_custom[0].colormap["mode"] == "custom"
        assert len(result_custom[0].colormap["stops"]) == 3

        result_from_path = node.load(filename="", path=path)
        assert len(result_from_path) == 1
        assert result_from_path[0].data.shape == (48, 64)

    print("  PASS\n")


def test_save_image():
    print("=== Test: SaveImage (Save Layers) ===")
    from backend.nodes.save_image import SaveImage
    import tifffile
    node = SaveImage()

    field_a = make_field(data=np.random.default_rng(4).random((32, 32)))
    field_b = make_field(data=np.random.default_rng(5).random((32, 32)))
    annotated = np.zeros((24, 24, 3), dtype=np.uint8)
    annotated[..., 0] = 255

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save single layer as TIFF
        tiff_path = os.path.join(tmpdir, "out.tiff")
        node.save(filename=tiff_path, format="TIFF", field_0=field_a)
        assert os.path.exists(tiff_path), "TIFF file not created"
        from PIL import Image
        im = Image.open(tiff_path)
        assert im.n_frames == 1
        arr_back = np.array(im)
        assert arr_back.shape == (32, 32)

        # Save multi-layer as TIFF
        tiff_path2 = os.path.join(tmpdir, "multi.tiff")
        node.save(filename=tiff_path2, format="TIFF", field_0=field_a, field_1=field_b)
        im2 = Image.open(tiff_path2)
        assert im2.n_frames == 2

        # Save annotated image as TIFF with layer name
        annotated_tiff = os.path.join(tmpdir, "annotated.tiff")
        node.save(
            filename=annotated_tiff,
            format="TIFF",
            field_0=annotated,
            layer_name_0="annotated overview",
        )
        with tifffile.TiffFile(annotated_tiff) as tif:
            assert len(tif.pages) == 1
            assert tif.pages[0].description == "annotated overview"
            assert tif.pages[0].asarray().shape == annotated.shape

        # Save as NPZ with layer names
        npz_path = os.path.join(tmpdir, "out.npz")
        node.save(
            filename=npz_path,
            format="NPZ",
            field_0=field_a,
            field_1=annotated,
            layer_name_0="height map",
            layer_name_1="annotated-overview",
        )
        assert os.path.exists(npz_path)
        npz = np.load(npz_path)
        assert len(npz.files) == 2
        assert np.allclose(npz["height_map"], field_a.data)
        assert np.array_equal(npz["annotated_overview"], annotated)

        # Extension is forced to match format
        wrong_ext = os.path.join(tmpdir, "output.png")
        node.save(filename=wrong_ext, format="TIFF", field_0=field_a)
        assert os.path.exists(os.path.join(tmpdir, "output.tiff"))

        # Directory input can drive the destination folder while filename supplies the basename
        driven_dir = os.path.join(tmpdir, "nested-output")
        node.save(filename="driven_name", directory=driven_dir, format="NPZ", field_0=field_a)
        assert os.path.exists(os.path.join(driven_dir, "driven_name.npz"))

        # Directory input rejects file paths
        try:
            node.save(
                filename="bad",
                directory=os.path.join(tmpdir, "looks_like_file.txt"),
                format="TIFF",
                field_0=field_a,
            )
            assert False, "Should have raised ValueError for file-like directory path"
        except ValueError:
            pass

        # No fields connected → error
        try:
            node.save(filename=os.path.join(tmpdir, "empty.tiff"), format="TIFF")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        # No filename → error
        try:
            node.save(filename="", format="TIFF", field_0=field_a)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    print("  PASS\n")


# =========================================================================
# Display (limited testing — these are output nodes with WS callbacks)
# =========================================================================

def test_color_map_node():
    print("=== Test: ColorMap ===")
    from backend.nodes.color_map import ColorMap

    node = ColorMap()

    preset, = node.build(mode="preset", preset="magma", stops_json="[]")
    assert preset["mode"] == "preset"
    assert preset["preset"] == "magma"

    custom, = node.build(
        mode="custom",
        preset="viridis",
        stops_json=json.dumps([
            {"position": 0.0, "color": "#000000"},
            {"position": 0.4, "color": "#00ff00"},
            {"position": 1.0, "color": "#ffffff"},
        ]),
    )
    assert custom["mode"] == "custom"
    assert custom["stops"][0]["position"] == 0.0
    assert custom["stops"][-1]["position"] == 1.0
    assert len(custom["stops"]) == 3
    print("  PASS\n")


def test_font_node():
    print("=== Test: Font ===")
    from backend.nodes.font_node import Font
    from backend.data_types import CUSTOM_FILE_FONT, SYSTEM_DEFAULT_FONT

    node = Font()

    system_default, = node.build(SYSTEM_DEFAULT_FONT)
    assert system_default is None

    named, = node.build("Arial")
    assert named == {"family": "Arial", "path": ""}

    custom, = node.build(CUSTOM_FILE_FONT, "/tmp/example-font.ttf")
    assert custom == {"family": "", "path": "/tmp/example-font.ttf"}
    print("  PASS\n")


def test_preview_image():
    print("=== Test: PreviewImage ===")
    from backend.nodes.preview_image import PreviewImage
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

    # Preview with field overlay metadata
    captured.clear()
    field_with_overlay = field.replace(overlays=[{"kind": "annotation", "show_scale_bar": True, "show_color_map": False, "text_size": 14.0}])
    node.preview(colormap="viridis", field=field_with_overlay)
    assert len(captured) == 1
    assert captured[0].startswith("data:image/png;base64,")

    # Preview with a custom colormap input
    captured.clear()
    custom_colormap = {
        "mode": "custom",
        "stops": [
            {"position": 0.0, "color": "#000000"},
            {"position": 0.5, "color": "#ff0000"},
            {"position": 1.0, "color": "#ffffff"},
        ],
    }
    node.preview(colormap="auto", field=field, colormap_map=custom_colormap)
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


def test_annotations():
    print("=== Test: Annotations ===")
    from backend.nodes.annotations import Annotations
    from backend.nodes.font_node import Font
    from backend.data_types import ImageData

    node = Annotations()
    font_node = Font()
    warnings = []
    Annotations._broadcast_warning_fn = lambda nid, msg: warnings.append(msg)
    Annotations._current_node_id = "test"
    field = DataField(
        data=np.linspace(0.0, 1.0, 64 * 64, dtype=np.float64).reshape(64, 64),
        xreal=1e-6,
        yreal=1e-6,
        si_unit_xy="m",
        si_unit_z="V",
        colormap="viridis",
    )

    base = datafield_to_uint8(field, "viridis")
    plain_preview = render_datafield_preview(field, "viridis")
    assert np.array_equal(plain_preview, base)

    plain_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=False)
    assert isinstance(plain_field, DataField)
    assert np.array_equal(plain_field.data, field.data)
    assert plain_field.colormap == "viridis"
    assert plain_field.overlays[-1]["kind"] == "annotation"
    plain = render_datafield_preview(plain_field, plain_field.colormap)
    assert plain.shape == base.shape
    assert np.array_equal(plain, base)

    with_scale_field, = node.render(input=field, colormap="auto", show_scale_bar=True, show_color_map=False)
    with_scale = render_datafield_preview(with_scale_field, with_scale_field.colormap)
    assert with_scale.shape == base.shape
    assert not np.array_equal(with_scale, base)

    with_legend_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=True)
    with_legend = render_datafield_preview(with_legend_field, with_legend_field.colormap)
    assert with_legend.shape[0] == base.shape[0]
    assert with_legend.shape[1] > base.shape[1]
    assert with_legend.shape[2] == 3

    larger_legend_field, = node.render(
        input=field,
        colormap="auto",
        show_scale_bar=False,
        show_color_map=True,
        text_size=28.0,
    )
    larger_legend_text = render_datafield_preview(larger_legend_field, larger_legend_field.colormap)
    assert larger_legend_text.shape == with_legend.shape
    assert not np.array_equal(larger_legend_text, with_legend)

    annotation_font, = font_node.build("Arial")
    with_font_field, = node.render(
        input=field,
        colormap="auto",
        show_scale_bar=False,
        show_color_map=True,
        text_size=28.0,
        font=annotation_font,
    )
    assert with_font_field.overlays[-1]["font"] == {"family": "Arial", "path": ""}
    with_font = render_datafield_preview(with_font_field, with_font_field.colormap)
    assert with_font.shape == with_legend.shape

    with_both_field, = node.render(input=field, colormap="auto", show_scale_bar=True, show_color_map=True)
    with_both = render_datafield_preview(with_both_field, with_both_field.colormap)
    assert with_both.shape == with_legend.shape
    assert not np.array_equal(with_both[:, :base.shape[1]], base)

    viewport_image = ImageData(
        np.zeros((48, 64, 3), dtype=np.uint8),
        metadata={
            "annotation_context": {
                "xreal": 2e-6,
                "si_unit_xy": "m",
                "legend_min": -1.5,
                "legend_mid": 0.0,
                "legend_max": 1.5,
                "legend_unit": "V",
                "colormap": "viridis",
            },
        },
    )
    annotated_image, = node.render(
        input=viewport_image,
        colormap="auto",
        show_scale_bar=True,
        show_color_map=True,
        text_size=18.0,
    )
    assert isinstance(annotated_image, ImageData)
    assert annotated_image.shape[0] == viewport_image.shape[0]
    assert annotated_image.shape[1] > viewport_image.shape[1]
    assert annotated_image.metadata["annotation_context"]["legend_unit"] == "V"
    assert not np.array_equal(np.asarray(annotated_image)[:, :viewport_image.shape[1]], np.asarray(viewport_image))
    assert warnings == []

    plain_image = ImageData(np.zeros((32, 40, 3), dtype=np.uint8))
    passthrough_image, = node.render(
        input=plain_image,
        colormap="auto",
        show_scale_bar=True,
        show_color_map=True,
        text_size=18.0,
    )
    assert isinstance(passthrough_image, ImageData)
    assert passthrough_image.shape == plain_image.shape
    assert np.array_equal(np.asarray(passthrough_image), np.asarray(plain_image))
    assert len(warnings) == 1
    assert "no scale metadata" in warnings[0]

    Annotations._broadcast_warning_fn = None

    print("  PASS\n")


def test_markup():
    print("=== Test: Markup ===")
    from backend.nodes.markup import Markup
    from backend.data_types import ImageData, _preview_markup_stroke_width

    node = Markup()
    field = make_field(data=np.linspace(0.0, 1.0, 48 * 48, dtype=np.float64).reshape(48, 48))
    base = render_datafield_preview(field, field.colormap)

    assert _preview_markup_stroke_width(5, 128, 128) == 5
    assert _preview_markup_stroke_width(5, 2048, 2048) > 5

    overlays = []
    Markup._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    Markup._current_node_id = "test"

    plain_field, = node.process(
        input=field,
        shape="line",
        stroke_color="#ffd54f",
        stroke_width=3,
        markup_shapes="[]",
    )
    assert isinstance(plain_field, DataField)
    assert plain_field.overlays[-1]["kind"] == "markup"
    plain = render_datafield_preview(plain_field, plain_field.colormap)
    assert np.array_equal(plain, base)
    assert overlays[-1]["kind"] == "markup"
    assert overlays[-1]["image"].startswith("data:image/png;base64,")

    shapes = json.dumps([
        {"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 3, "color": "#ff0000"},
        {"kind": "rectangle", "x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.5, "width": 2, "color": "#00ff00"},
        {"kind": "circle", "x1": 0.25, "y1": 0.55, "x2": 0.55, "y2": 0.85, "width": 2, "color": "#4fc3f7"},
        {"kind": "arrow", "x1": 0.15, "y1": 0.85, "x2": 0.85, "y2": 0.2, "width": 4, "color": "#ffffff"},
    ])
    marked_field, = node.process(
        input=field,
        shape="arrow",
        stroke_color="#ffffff",
        stroke_width=4,
        markup_shapes=shapes,
    )
    marked = render_datafield_preview(marked_field, marked_field.colormap)
    assert marked.shape == base.shape
    assert not np.array_equal(marked, base)

    viewport_image = ImageData(
        np.zeros((48, 48, 3), dtype=np.uint8),
        metadata={"annotation_context": {"xreal": 1e-6, "si_unit_xy": "m"}},
    )
    image_markup, = node.process(
        input=viewport_image,
        shape="line",
        stroke_color="#ff0000",
        stroke_width=4,
        markup_shapes=json.dumps([
            {"kind": "line", "x1": 0.1, "y1": 0.2, "x2": 0.9, "y2": 0.8, "width": 4, "color": "#ff0000"},
        ]),
    )
    assert isinstance(image_markup, ImageData)
    assert image_markup.metadata["annotation_context"]["si_unit_xy"] == "m"
    assert not np.array_equal(np.asarray(image_markup), np.asarray(viewport_image))

    Markup._broadcast_overlay_fn = None
    print("  PASS\n")


def test_print_table():
    print("=== Test: PrintTable ===")
    from backend.nodes.print_table import PrintTable
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


def test_value_display():
    print("=== Test: ValueDisplay ===")
    from backend.nodes.value_display import ValueDisplay

    node = ValueDisplay()
    captured = []
    ValueDisplay._broadcast_value_fn = lambda node_id, payload: captured.append((node_id, payload))
    ValueDisplay._current_node_id = "test"

    result = node.display_value(3.25)
    assert result == (3.25,)
    assert captured == [("test", {"value": 3.25})]

    measurements = MeasureTable([
        {"quantity": "delta X", "value": 1.7e-7, "unit": "m"},
        {"quantity": "delta Y", "value": 463, "unit": "count"},
    ])
    result = node.display_value(measurements, measurement="delta X")
    assert result == (1.7e-7,)
    assert captured[-1] == ("test", {"value": 1.7e-7, "unit": "m"})

    ValueDisplay._broadcast_value_fn = None
    print("  PASS\n")


# =========================================================================
# I/O — IBW multi-channel loading
# =========================================================================

def test_load_file_ibw():
    print("=== Test: Image IBW multi-channel ===")
    from backend.nodes.image import Image

    node = Image()
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
    print("=== Test: Image .npz ===")
    from backend.nodes.image import Image

    node = Image()
    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.random.default_rng(99).standard_normal((30, 40))
        path = os.path.join(tmpdir, "test.npz")
        np.savez(path, my_array=data)

        result = node.load(filename=path)
        assert len(result) == 1
        assert np.allclose(result[0].data, data)

    print("  PASS\n")


def test_load_file_cache():
    print("=== Test: Image cache ===")
    from unittest.mock import patch
    from backend.nodes.image import Image

    node = Image()
    Image._load_fields_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.arange(16, dtype=np.float64).reshape(4, 4)
        path = os.path.join(tmpdir, "cached.npy")
        np.save(path, data)

        with patch.object(Image, "_load_image_or_array", wraps=Image._load_image_or_array) as loader:
            first, = node.load(filename=path)
            second, = node.load(filename=path)
            assert loader.call_count == 1

        assert np.allclose(first.data, data)
        assert np.allclose(second.data, data)
        assert first is not second
        first.data[0, 0] = -999.0

        third, = node.load(filename=path)
        assert third.data[0, 0] == data[0, 0]

    Image._load_fields_cached.cache_clear()
    print("  PASS\n")


def test_load_file_not_found():
    print("=== Test: Image not found ===")
    from backend.nodes.image import Image

    node = Image()
    try:
        node.load(filename="/nonexistent/path/file.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass

    print("  PASS\n")


def test_load_file_unsupported():
    print("=== Test: Image unsupported format ===")
    from backend.nodes.image import Image

    node = Image()
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
    print("=== Test: Image warning for uncalibrated data ===")
    from backend.nodes.image import Image as ImageNode
    from PIL import Image as PILImage

    node = ImageNode()
    warnings = []
    ImageNode._broadcast_warning_fn = lambda nid, msg: warnings.append(msg)
    ImageNode._current_node_id = "test"

    with tempfile.TemporaryDirectory() as tmpdir:
        arr = np.random.default_rng(10).integers(0, 256, (16, 16), dtype=np.uint8)
        img = PILImage.fromarray(arr)
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 1
        assert len(warnings) == 1
        assert "Uncalibrated" in warnings[0]

    ImageNode._broadcast_warning_fn = None
    print("  PASS\n")


# =========================================================================
# I/O — list_channels helper
# =========================================================================

def test_list_channels():
    print("=== Test: list_channels ===")
    from backend.nodes.helpers import list_channels, list_folder_paths
    from backend.nodes.folder import Folder
    from PIL import Image

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

    with tempfile.TemporaryDirectory() as tmpdir:
        img = Image.fromarray(np.zeros((8, 8), dtype=np.uint8))
        png_path = os.path.join(tmpdir, "a.png")
        npy_path = os.path.join(tmpdir, "b.npy")
        gwy_path = os.path.join(tmpdir, "c.gwy")
        sxm_path = os.path.join(tmpdir, "d.sxm")
        ibw_path = os.path.join(tmpdir, "e.ibw")
        txt_path = os.path.join(tmpdir, "notes.txt")
        img.save(png_path)
        np.save(npy_path, np.zeros((4, 4)))
        Path(gwy_path).write_bytes(b"gwy")
        Path(sxm_path).write_bytes(b"sxm")
        Path(ibw_path).write_bytes(b"ibw")
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write("ignore me")

        paths = list_folder_paths(tmpdir)
        assert [entry["name"] for entry in paths] == ["directory", "a.png", "b.npy", "c.gwy", "d.sxm", "e.ibw"]
        assert Path(paths[0]["path"]).resolve() == Path(tmpdir).resolve()
        assert paths[0]["type"] == "DIRECTORY"
        assert all(entry["type"] == "FILE_PATH" for entry in paths[1:])

        folder_node = Folder()
        folder_result = folder_node.list_files(tmpdir)
        assert folder_result == tuple(entry["path"] for entry in paths)

    print("  PASS\n")


# =========================================================================
# I/O — ImageDemo
# =========================================================================

def test_load_demo():
    print("=== Test: ImageDemo ===")
    from backend.nodes.image_demo import ImageDemo

    node = ImageDemo()

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


def test_load_demo_cache():
    print("=== Test: ImageDemo cache ===")
    from unittest.mock import patch
    from backend.nodes.image import Image
    from backend.nodes.image_demo import ImageDemo

    node = ImageDemo()
    Image._load_fields_cached.cache_clear()

    with patch.object(Image, "_load_image_or_array", wraps=Image._load_image_or_array) as loader:
        first, = node.load(name="nanoparticles.npy")
        second, = node.load(name="nanoparticles.npy")
        assert loader.call_count == 1

    assert np.allclose(first.data, second.data)
    assert first is not second
    first.data[0, 0] = -999.0

    third, = node.load(name="nanoparticles.npy")
    assert third.data[0, 0] != -999.0

    Image._load_fields_cached.cache_clear()
    print("  PASS\n")


def test_load_demo_multi_layer_preview_payload():
    print("=== Test: ImageDemo multi-layer preview payload ===")
    from backend.execution import ExecutionEngine
    import backend.nodes  # noqa: F401

    previews = []
    prompt = {
        "1": {
            "class_type": "ImageDemo",
            "inputs": {
                "name": "whiskers.ibw",
                "colormap": "viridis",
            },
        },
    }

    ExecutionEngine().execute(prompt, on_preview=lambda node_id, payload: previews.append((node_id, payload)))

    assert len(previews) == 1
    node_id, payload = previews[0]
    assert node_id == "1"
    assert payload["kind"] == "layer_gallery"
    assert len(payload["layers"]) == 4
    assert all(isinstance(layer["name"], str) and layer["name"] for layer in payload["layers"])
    assert all(layer["image"].startswith("data:image/png;base64,") for layer in payload["layers"])

    print("  PASS\n")


# =========================================================================
# I/O — Coordinate
# =========================================================================

def test_coordinate():
    print("=== Test: Coordinate ===")
    from backend.nodes.coordinate import Coordinate

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
# I/O — Number
# =========================================================================

def test_number():
    print("=== Test: Number ===")
    from backend.nodes.number import Number

    node = Number()

    result = node.process(value=1.25)
    assert result == (1.25,)

    result_neg = node.process(value=-3.5)
    assert result_neg == (-3.5,)

    print("  PASS\n")


def test_range_slider():
    print("=== Test: RangeSlider ===")
    from backend.nodes.range_slider import RangeSlider

    node = RangeSlider()

    result = node.process(min_value=0.0, max_value=10.0, value=3.25)
    assert result == (3.25,)

    # Clamp above max
    result_high = node.process(min_value=0.0, max_value=10.0, value=12.0)
    assert result_high == (10.0,)

    # Reversed bounds should still work
    result_reversed = node.process(min_value=5.0, max_value=-1.0, value=4.0)
    assert result_reversed == (4.0,)

    # Equal bounds collapse to a fixed value
    result_fixed = node.process(min_value=2.5, max_value=2.5, value=99.0)
    assert result_fixed == (2.5,)

    print("  PASS\n")


def test_execution_engine_numeric_socket_coercion():
    print("=== Test: ExecutionEngine numeric socket coercion ===")
    from backend.execution import ExecutionEngine
    from backend.node_registry import register_node

    @register_node(display_name="Test Echo Int")
    class TestEchoInt:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("INT",)}}

        RETURN_TYPES = ("INT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            return (value,)

    @register_node(display_name="Test Echo Float")
    class TestEchoFloat:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}

        RETURN_TYPES = ("FLOAT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            return (value,)

    engine = ExecutionEngine()
    prompt = {
        "1": {
            "class_type": "Number",
            "inputs": {"value": 3.6},
        },
        "2": {
            "class_type": "TestEchoInt",
            "inputs": {"value": ["1", 0]},
        },
        "3": {
            "class_type": "TestEchoFloat",
            "inputs": {"value": ["1", 0]},
        },
    }

    outputs = engine.execute(prompt)
    assert outputs["2"] == (4,)
    assert outputs["3"] == (3.6,)

    print("  PASS\n")


def test_execution_engine_caches_unchanged_nodes():
    print("=== Test: ExecutionEngine caches unchanged nodes ===")
    from backend.execution import ExecutionEngine
    from backend.node_registry import register_node

    @register_node(display_name="Test Cache Source")
    class TestCacheSource:
        calls = 0

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}

        RETURN_TYPES = ("FLOAT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            TestCacheSource.calls += 1
            return (float(value),)

    @register_node(display_name="Test Cache Downstream")
    class TestCacheDownstream:
        calls = 0

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}

        RETURN_TYPES = ("FLOAT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            TestCacheDownstream.calls += 1
            return (float(value) * 2.0,)

    TestCacheSource.calls = 0
    TestCacheDownstream.calls = 0

    engine = ExecutionEngine()
    prompt = {
        "1": {
            "class_type": "TestCacheSource",
            "inputs": {"value": 2.5},
        },
        "2": {
            "class_type": "TestCacheDownstream",
            "inputs": {"value": ["1", 0]},
        },
    }

    first_timings = []
    first_outputs = engine.execute(prompt, on_node_done=lambda node_id, elapsed_ms: first_timings.append((node_id, elapsed_ms)))
    second_timings = []
    second_outputs = engine.execute(prompt, on_node_done=lambda node_id, elapsed_ms: second_timings.append((node_id, elapsed_ms)))

    assert first_outputs["2"] == (5.0,)
    assert second_outputs["2"] == (5.0,)
    assert TestCacheSource.calls == 1
    assert TestCacheDownstream.calls == 1
    assert {node_id for node_id, _ in second_timings} == {"1", "2"}
    assert all(elapsed_ms == 0.0 for _, elapsed_ms in second_timings)

    print("  PASS\n")


def test_execution_engine_only_propagates_real_output_changes():
    print("=== Test: ExecutionEngine propagates only real upstream output changes ===")
    from backend.execution import ExecutionEngine
    from backend.node_registry import register_node

    @register_node(display_name="Test Quantized Source")
    class TestQuantizedSource:
        calls = 0

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}

        RETURN_TYPES = ("INT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            TestQuantizedSource.calls += 1
            return (int(round(float(value))),)

    @register_node(display_name="Test Quantized Downstream")
    class TestQuantizedDownstream:
        calls = 0

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("INT",)}}

        RETURN_TYPES = ("FLOAT",)
        RETURN_NAMES = ("value",)
        FUNCTION = "process"
        CATEGORY = "tests"

        def process(self, value):
            TestQuantizedDownstream.calls += 1
            return (float(value) + 0.5,)

    TestQuantizedSource.calls = 0
    TestQuantizedDownstream.calls = 0

    engine = ExecutionEngine()
    prompt = {
        "1": {
            "class_type": "TestQuantizedSource",
            "inputs": {"value": 1.2},
        },
        "2": {
            "class_type": "TestQuantizedDownstream",
            "inputs": {"value": ["1", 0]},
        },
    }

    outputs_first = engine.execute(prompt)
    assert outputs_first["2"] == (1.5,)

    prompt["1"]["inputs"]["value"] = 1.3
    outputs_second = engine.execute(prompt)
    assert outputs_second["2"] == (1.5,)

    prompt["1"]["inputs"]["value"] = 2.2
    outputs_third = engine.execute(prompt)
    assert outputs_third["2"] == (2.5,)

    assert TestQuantizedSource.calls == 3
    assert TestQuantizedDownstream.calls == 2

    print("  PASS\n")


# =========================================================================
# Analysis — Cursors
# =========================================================================

def test_line_cursors():
    print("=== Test: Cursors ===")
    from backend.nodes.cursors import Cursors

    node = Cursors()

    # Create a simple linear ramp
    line = np.linspace(0, 10, 100).astype(np.float64)

    # Capture overlay
    overlays = []
    Cursors._broadcast_overlay_fn = lambda nid, data: overlays.append(data)
    Cursors._current_node_id = "test"

    table, coord_pair = node.process(line, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
    assert isinstance(coord_pair, tuple) and len(coord_pair) == 2

    # Should produce a 6-row table
    assert len(table) == 6
    quantities = {row["quantity"] for row in table}
    assert "A x" in quantities
    assert "B x" in quantities
    assert "dx" in quantities
    assert "dy" in quantities

    # B should be at a later position than A
    a_pos = next(r["value"] for r in table if r["quantity"] == "A x")
    b_pos = next(r["value"] for r in table if r["quantity"] == "B x")
    assert b_pos > a_pos

    # Delta Y should reflect the height difference along the ramp
    dy = next(r["value"] for r in table if r["quantity"] == "dy")
    assert dy > 0  # ramp goes upward

    # Overlay should have been broadcast
    assert len(overlays) == 1
    assert overlays[0]["kind"] == "line_plot"
    assert len(overlays[0]["line"]) == len(line)
    assert len(overlays[0]["x_axis"]) == len(line)
    assert 0.0 <= overlays[0]["x1"] <= 1.0
    assert 0.0 <= overlays[0]["x2"] <= 1.0

    # With LineData input (which carries its own x_axis)
    line_data = LineData(data=line, x_axis=np.linspace(0, 1, 100))
    table2, _ = node.process(line_data, x1=0.25, y1=0.5, x2=0.75, y2=0.5)
    assert len(table2) == 6

    # Field input should report dx/dy/dz and broadcast an image overlay
    field = DataField(
        data=np.arange(100, dtype=np.float64).reshape(10, 10),
        xreal=2.0,
        yreal=4.0,
        si_unit_xy="um",
        si_unit_z="nm",
    )
    overlays.clear()
    table3, _ = node.process(field, x1=0.2, y1=0.25, x2=0.7, y2=0.75)
    assert len(table3) == 9
    field_rows = {row["quantity"]: row for row in table3}
    assert field_rows["dx"]["unit"] == "um"
    assert field_rows["dy"]["unit"] == "um"
    assert field_rows["dz"]["unit"] == "nm"
    assert np.isclose(field_rows["dx"]["value"], 1.0)
    assert np.isclose(field_rows["dy"]["value"], 2.0)
    assert len(overlays) == 1
    assert overlays[0]["kind"] == "cursor_points"
    assert overlays[0]["image"].startswith("data:image/png;base64,")

    Cursors._broadcast_overlay_fn = None
    print("  PASS\n")


# =========================================================================
# Analysis — FFT2D
# =========================================================================

def test_fft2d():
    print("=== Test: FFT2D ===")
    from backend.nodes.fft_2d import FFT2D

    node = FFT2D()

    # Pure single-frequency signal: peak should appear at the right location
    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    freq = 5
    data = np.sin(2 * np.pi * freq * x)
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    # log_magnitude
    spectrum, spec_mag, spec_phase, spec_psdf = node.process(field, windowing="none", level="none")
    assert spectrum.data.shape == (N, N)
    assert spectrum.domain == "frequency"
    assert spectrum.si_unit_xy == "1/m"
    # Peak should be symmetric about centre
    centre = N // 2
    row = spectrum.data[centre, :]
    peak_idx = np.argmax(row[centre + 1:]) + centre + 1
    assert abs(peak_idx - (centre + freq)) <= 1, f"Peak at {peak_idx}, expected ~{centre + freq}"

    # magnitude output
    _, spec_mag, _, _ = node.process(field, windowing="hann", level="mean")
    assert spec_mag.data.shape == (N, N)
    assert np.all(spec_mag.data >= 0)

    # phase output
    _, _, spec_phase, _ = node.process(field, windowing="none", level="none")
    assert spec_phase.data.shape == (N, N)
    assert spec_phase.data.min() >= -np.pi - 0.01
    assert spec_phase.data.max() <= np.pi + 0.01

    # psdf output — units should reflect PSDF calibration
    _, _, _, spec_psdf = node.process(field, windowing="hamming", level="plane")
    assert spec_psdf.data.shape == (N, N)
    assert np.all(spec_psdf.data >= 0)
    assert "^2" in spec_psdf.si_unit_z

    # Constant field should have all energy at DC
    const_field = make_field(data=np.ones((32, 32)) * 3.0)
    _, spec_const, _, _ = node.process(const_field, windowing="none", level="none")
    centre32 = 16
    dc_val = spec_const.data[centre32, centre32]
    assert dc_val == spec_const.data.max(), "DC should be the maximum for constant field"

    # Blackman windowing should also work without error
    spec_bk, _, _, _ = node.process(field, windowing="blackman", level="none")
    assert spec_bk.data.shape == (N, N)

    print("  PASS\n")


# =========================================================================
# Analysis — Stats
# =========================================================================

def test_stats():
    print("=== Test: Stats ===")
    from backend.nodes.stats import Stats

    node = Stats()
    captured = []
    Stats._broadcast_value_fn = lambda node_id, payload: captured.append((node_id, payload))
    Stats._current_node_id = "test"

    line = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    result, = node.process(line, operation="mean", column="value")
    assert np.isclose(result, 2.5)
    assert captured[-1] == ("test", {"value": result})
    roughness, = node.process(line, operation="Rq", column="value")
    assert np.isclose(roughness, np.sqrt(np.mean((line - line.mean()) ** 2)))

    table = RecordTable([
        {"name": "a", "value": 3.0, "unit": "m", "other": 10.0},
        {"name": "b", "value": 7.0, "unit": "m", "other": 20.0},
    ])
    result, = node.process(table, operation="max", column="value")
    assert result == 7.0
    assert captured[-1] == ("test", {"value": 7.0, "unit": "m"})
    count, = node.process(table, operation="count", column="other")
    assert count == 2.0
    auto_column_range, = node.process(table, operation="range", column="")
    assert auto_column_range == 4.0

    field = make_field(data=np.array([[1.0, 5.0], [2.0, 4.0]], dtype=np.float64))
    result, = node.process(field, operation="range", column="value")
    assert result == 4.0
    assert captured[-1] == ("test", {"value": 4.0, "unit": "m"})

    image = np.array([[0, 10], [20, 30]], dtype=np.uint8)
    result, = node.process(image, operation="avg", column="value")
    assert np.isclose(result, 15.0)
    assert captured[-1] == ("test", {"value": 15.0})

    try:
        node.process(table, operation="Rq", column="value")
        raise AssertionError("Expected invalid TABLE operation to raise ValueError")
    except ValueError:
        pass

    try:
        node.process([{"label": "only text"}], operation="max", column="label")
        raise AssertionError("Expected non-numeric record-table input to raise ValueError")
    except ValueError:
        pass

    try:
        node.process(
            MeasureTable([{"quantity": "min", "value": 1.0, "unit": "m"}]),
            operation="max",
            column="value",
        )
        raise AssertionError("Expected measurement table input to raise ValueError")
    except ValueError:
        pass

    Stats._broadcast_value_fn = None
    print("  PASS\n")


# =========================================================================
# Display — View3D
# =========================================================================

def test_view3d():
    print("=== Test: View3D ===")
    from backend.nodes.view_3d import View3D
    from backend.data_types import ImageData, MeshModel
    from backend.execution_context import active_node, execution_callbacks
    import base64
    import io
    from PIL import Image

    node = View3D()
    field = make_field()

    captured = []
    mesh_callback = lambda nid, mesh: captured.append(mesh)

    preview_image = Image.new("RGB", (12, 10), (255, 0, 0))
    preview_buffer = io.BytesIO()
    preview_image.save(preview_buffer, format="PNG")
    viewport_snapshot = "data:image/png;base64," + base64.b64encode(preview_buffer.getvalue()).decode()

    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        result = node.render(
            field,
            colormap="viridis",
            z_scale=2.0,
            resolution=64,
            make_solid=False,
            camera_target_x=0.1,
            camera_target_y=-0.2,
            camera_target_z=0.3,
            viewport_snapshot=viewport_snapshot,
        )
    assert len(result) == 2
    assert isinstance(result[0], MeshModel)
    assert isinstance(result[1], ImageData)
    assert result[1].shape == (10, 12, 3)
    assert np.all(result[1][0, 0] == np.array([255, 0, 0], dtype=np.uint8))
    assert result[1].metadata["annotation_context"]["si_unit_xy"] == field.si_unit_xy
    assert result[1].metadata["viewport_camera"]["target_x"] == 0.1
    assert result[1].metadata["viewport_camera"]["target_y"] == -0.2
    assert result[1].metadata["viewport_camera"]["target_z"] == 0.3
    assert len(captured) == 1

    mesh = captured[0]
    assert "width" in mesh
    assert "height" in mesh
    assert "z_data" in mesh
    assert "colors" in mesh
    assert mesh["z_scale"] == 0.2
    assert mesh["width"] <= 64
    assert mesh["height"] <= 64
    assert mesh["camera_target_x"] == 0.1
    assert mesh["camera_target_y"] == -0.2
    assert mesh["camera_target_z"] == 0.3
    # z_min < z_max for non-constant data
    assert mesh["z_min"] < mesh["z_max"]

    # Verify base64 data can be decoded
    z_bytes = base64.b64decode(mesh["z_data"])
    assert len(z_bytes) == mesh["width"] * mesh["height"] * 4  # float32

    colors_bytes = base64.b64decode(mesh["colors"])
    assert len(colors_bytes) == mesh["width"] * mesh["height"] * 3  # uint8 RGB

    # High-res input should be downsampled
    big_field = make_field(shape=(256, 256))
    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        node.render(big_field, colormap="hot", z_scale=1.0, resolution=64, make_solid=False)
    assert captured[0]["width"] <= 64
    assert captured[0]["height"] <= 64

    # Separate map input should affect colors without changing mesh geometry
    mesh_field = make_field(data=np.zeros((64, 64), dtype=np.float64), xreal=2.0, yreal=3.0)
    map_field = make_field(data=np.tile(np.linspace(0.0, 1.0, 64, dtype=np.float64), (64, 1)), xreal=2.0, yreal=3.0)
    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        mapped_result = node.render(mesh_field, map_field=map_field, colormap="viridis", z_scale=1.0, resolution=32, make_solid=False)
    mapped_mesh = captured[0]
    assert mapped_mesh["x_range"] == [float(mesh_field.xoff), float(mesh_field.xoff + mesh_field.xreal)]
    assert mapped_mesh["y_range"] == [float(mesh_field.yoff), float(mesh_field.yoff + mesh_field.yreal)]
    assert np.isclose(mapped_mesh["surface_extent_x"] / mapped_mesh["surface_extent_y"], mesh_field.xreal / mesh_field.yreal)
    mapped_z = np.frombuffer(base64.b64decode(mapped_mesh["z_data"]), dtype=np.float32)
    assert np.allclose(mapped_z, 0.0)
    mapped_colors = np.frombuffer(base64.b64decode(mapped_mesh["colors"]), dtype=np.uint8)
    top_vertices = np.asarray(mapped_result[0].vertices, dtype=np.float32)
    x_span = float(top_vertices[:, 0].max() - top_vertices[:, 0].min())
    y_span = float(top_vertices[:, 2].max() - top_vertices[:, 2].min())
    assert np.isclose(x_span / y_span, mesh_field.xreal / mesh_field.yreal)

    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        node.render(mesh_field, colormap="viridis", z_scale=1.0, resolution=32, make_solid=False)
    mesh_only = captured[0]
    mesh_only_colors = np.frombuffer(base64.b64decode(mesh_only["colors"]), dtype=np.uint8)
    assert not np.array_equal(mapped_colors, mesh_only_colors)

    # make_solid should add extra geometry beyond the top surface grid
    solid_mesh = mapped_result[0]
    assert isinstance(solid_mesh, MeshModel)
    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        solid_result = node.render(mesh_field, colormap="viridis", z_scale=1.0, resolution=16, make_solid=True)
    assert len(solid_result[0].vertices) > 16 * 16
    assert len(solid_result[0].faces) > (15 * 15 * 2)
    solid_payload = captured[0]
    assert solid_payload["make_solid"] is True
    assert "positions" in solid_payload
    assert "indices" in solid_payload
    assert "vertex_colors" in solid_payload
    print("  PASS\n")


def test_save_generic():
    print("=== Test: Save ===")
    from backend.nodes.save import Save
    from backend.data_types import DataField, ImageData, LineData, MeasureTable, MeshModel, RecordTable
    import tifffile
    from PIL import Image as PILImage

    node = Save()
    format_choices = node.INPUT_TYPES()["required"]["format"][1]["choices_by_source_type"]
    assert format_choices["ANNOTATION_SOURCE"] == format_choices["IMAGE"]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save scalar as TXT and JSON
        node.save(filename="scalar", directory_path=tmpdir, format="TXT", value=3.5)
        assert Path(tmpdir, "scalar.txt").read_text(encoding="utf-8").strip() == "3.5"
        node.save(filename="scalar_json", directory_path=tmpdir, format="JSON", value=3.5)
        assert json.loads(Path(tmpdir, "scalar_json.json").read_text(encoding="utf-8")) == {"value": 3.5}

        # Save line as CSV, NPZ, and JSON
        line = LineData(data=np.array([1.0, 2.0, 3.0]), x_axis=np.array([0.0, 0.5, 1.0]), x_unit="um", y_unit="nm")
        node.save(filename="profile", directory_path=tmpdir, format="CSV", value=line)
        csv_text = Path(tmpdir, "profile.csv").read_text(encoding="utf-8")
        assert "x,y,x_unit,y_unit" in csv_text
        assert "um" in csv_text and "nm" in csv_text
        node.save(filename="profile_npz", directory_path=tmpdir, format="NPZ", value=line)
        line_npz = np.load(Path(tmpdir, "profile_npz.npz"))
        assert np.allclose(line_npz["x"], line.x_axis)
        assert np.allclose(line_npz["y"], line.data)
        node.save(filename="profile_json", directory_path=tmpdir, format="JSON", value=line)
        line_json = json.loads(Path(tmpdir, "profile_json.json").read_text(encoding="utf-8"))
        assert line_json["x_unit"] == "um"
        assert line_json["y_unit"] == "nm"
        assert line_json["x"] == [0.0, 0.5, 1.0]
        assert line_json["y"] == [1.0, 2.0, 3.0]

        # Save DATA_FIELD as TIFF, PNG, and NPZ
        field = DataField(
            data=np.array([[1.0, 2.0], [3.0, 4.5]], dtype=np.float64),
            xreal=2e-6,
            yreal=1e-6,
            si_unit_xy="m",
            si_unit_z="m",
            colormap="viridis",
        )
        node.save(filename="field_tiff", directory_path=tmpdir, format="TIFF", value=field)
        field_tiff = tifffile.imread(Path(tmpdir, "field_tiff.tiff"))
        assert field_tiff.shape == field.data.shape
        assert field_tiff.dtype == np.float32
        assert np.allclose(field_tiff, field.data.astype(np.float32))

        node.save(filename="field_png", directory_path=tmpdir, format="PNG", value=field)
        field_png = np.asarray(PILImage.open(Path(tmpdir, "field_png.png")))
        assert field_png.shape == (2, 2, 3)
        assert field_png.dtype == np.uint8

        node.save(filename="field_npz", directory_path=tmpdir, format="NPZ", value=field)
        field_npz = np.load(Path(tmpdir, "field_npz.npz"))
        assert np.allclose(field_npz["field"], field.data)

        # Save IMAGE as PNG, TIFF, and NPZ
        image = np.array(
            [
                [[255, 0, 0], [0, 255, 0]],
                [[0, 0, 255], [255, 255, 0]],
            ],
            dtype=np.uint8,
        )
        node.save(filename="image_png", directory_path=tmpdir, format="PNG", value=image)
        image_png = np.asarray(PILImage.open(Path(tmpdir, "image_png.png")))
        assert image_png.shape == image.shape
        assert np.array_equal(image_png, image)

        node.save(filename="image_tiff", directory_path=tmpdir, format="TIFF", value=image)
        image_tiff = tifffile.imread(Path(tmpdir, "image_tiff.tiff"))
        assert image_tiff.shape == image.shape
        assert image_tiff.dtype == np.uint8
        assert np.array_equal(image_tiff, image)

        node.save(filename="image_npz", directory_path=tmpdir, format="NPZ", value=image)
        image_npz = np.load(Path(tmpdir, "image_npz.npz"))
        assert np.array_equal(image_npz["image"], image)

        # Save ANNOTATION_SOURCE as PNG, TIFF, and NPZ
        annotation_image = ImageData(
            image,
            metadata={"annotation_context": {"si_unit_xy": "um", "si_unit_z": "nm"}},
        )
        node.save(filename="annotation_png", directory_path=tmpdir, format="PNG", value=annotation_image)
        annotation_png = np.asarray(PILImage.open(Path(tmpdir, "annotation_png.png")))
        assert annotation_png.shape == image.shape
        assert np.array_equal(annotation_png, image)

        node.save(filename="annotation_tiff", directory_path=tmpdir, format="TIFF", value=annotation_image)
        annotation_tiff = tifffile.imread(Path(tmpdir, "annotation_tiff.tiff"))
        assert annotation_tiff.shape == image.shape
        assert annotation_tiff.dtype == np.uint8
        assert np.array_equal(annotation_tiff, image)

        node.save(filename="annotation_npz", directory_path=tmpdir, format="NPZ", value=annotation_image)
        annotation_npz = np.load(Path(tmpdir, "annotation_npz.npz"))
        assert np.array_equal(annotation_npz["image"], image)

        # Save tables as CSV and JSON
        measure_table = MeasureTable([
            {"quantity": "Rq", "value": 1.23, "unit": "nm"},
            {"quantity": "Ra", "value": 0.98, "unit": "nm"},
        ])
        node.save(filename="measurements_csv", directory_path=tmpdir, format="CSV", value=measure_table)
        measure_csv = Path(tmpdir, "measurements_csv.csv").read_text(encoding="utf-8")
        assert "quantity,value,unit" in measure_csv
        assert "Rq,1.23,nm" in measure_csv
        node.save(filename="measurements_json", directory_path=tmpdir, format="JSON", value=measure_table)
        assert json.loads(Path(tmpdir, "measurements_json.json").read_text(encoding="utf-8")) == list(measure_table)

        record_table = RecordTable([
            {"label": "particle-1", "height": 12.0, "area": 44.0},
            {"label": "particle-2", "height": 8.0, "area": 21.0},
        ])
        node.save(filename="records_csv", directory_path=tmpdir, format="CSV", value=record_table)
        record_csv = Path(tmpdir, "records_csv.csv").read_text(encoding="utf-8")
        assert "label,height,area" in record_csv
        assert "particle-1,12.0,44.0" in record_csv
        node.save(filename="records_json", directory_path=tmpdir, format="JSON", value=record_table)
        assert json.loads(Path(tmpdir, "records_json.json").read_text(encoding="utf-8")) == list(record_table)

        # Save mesh as OBJ and STL
        mesh = MeshModel(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2]], dtype=np.int32),
        )
        node.save(filename="triangle", directory_path=tmpdir, format="OBJ", value=mesh)
        obj_text = Path(tmpdir, "triangle.obj").read_text(encoding="utf-8")
        assert "v 0.0 0.0 0.0" in obj_text
        assert "f 1 2 3" in obj_text

        node.save(filename="triangle", directory_path=tmpdir, format="STL", value=mesh)
        stl_text = Path(tmpdir, "triangle.stl").read_text(encoding="utf-8")
        assert stl_text.startswith("solid argonode")
        assert "facet normal" in stl_text

        try:
            node.save(filename="triangle", directory_path=tmpdir, format="PNG", value=mesh)
            assert False, "Mesh should only be saveable as OBJ or STL"
        except ValueError:
            pass

        try:
            node.save(filename="field_bad", directory_path=tmpdir, format="CSV", value=field)
            assert False, "DATA_FIELD should reject unsupported save formats"
        except ValueError:
            pass

    print("  PASS\n")


# =========================================================================
# Run all tests
# =========================================================================

if __name__ == "__main__":
    # Filters
    test_gaussian_filter()
    test_median_filter()
    test_crop_resize_field()
    test_rotate_field()
    test_colormap_adjust()
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
    test_stats()

    # Mask
    test_threshold_mask()
    test_mask_morphology()
    test_mask_invert()
    test_mask_combine()
    test_draw_mask()

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
    test_range_slider()
    test_save_generic()
    test_save_image()

    # Display
    test_preview_image()
    test_print_table()
    test_value_display()
    test_view3d()

    print("All tests passed!")
