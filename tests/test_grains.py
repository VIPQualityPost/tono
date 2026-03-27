"""
Thorough tests for the particles/particle analysis pipeline:
    ThresholdMask → GrainAnalysis

Covers synthetic geometry (known answers), the demo nanoparticles image,
edge cases, and physical-unit correctness.

Run from project root:
    .venv/bin/python -m tests.test_particles
"""

import sys
import numpy as np

sys.path.insert(0, ".")
from backend.data_types import DataField


def make_field(data, xreal=1e-6, yreal=1e-6):
    return DataField(data=data.astype(np.float64), xreal=xreal, yreal=yreal,
                     si_unit_xy="m", si_unit_z="m")


# =========================================================================
# ThresholdMask tests
# =========================================================================

def test_threshold_otsu_bimodal():
    """Otsu on a clean bimodal image should separate the two populations."""
    print("=== Test: Otsu on bimodal image ===")
    from backend.nodes.threshold_mask import ThresholdMask
    node = ThresholdMask()

    data = np.zeros((128, 128))
    data[30:50, 30:50] = 10.0   # bright square
    data[70:100, 80:110] = 10.0  # another bright region
    field = make_field(data)

    mask, = node.process(field, method="otsu", threshold=0.0, direction="above")
    bright_pixels = (mask == 255)
    # Should capture both bright regions
    assert bright_pixels[40, 40], "Otsu missed bright region 1"
    assert bright_pixels[85, 95], "Otsu missed bright region 2"
    # Background should be dark
    assert not bright_pixels[0, 0], "Otsu false positive in background"
    assert not bright_pixels[60, 60], "Otsu false positive between regions"
    print("  PASS\n")


def test_threshold_relative_range():
    """Relative threshold at 0.5 should be the midpoint of [min, max]."""
    print("=== Test: Relative threshold at midpoint ===")
    from backend.nodes.threshold_mask import ThresholdMask
    node = ThresholdMask()

    data = np.full((64, 64), 2.0)
    data[10:20, 10:20] = 8.0  # bright patch, range = [2, 8], midpoint = 5
    field = make_field(data)

    mask, = node.process(field, method="relative", threshold=0.5, direction="above")
    # Only the bright patch (value 8 >= 5) should be masked
    assert np.all(mask[10:20, 10:20] == 255)
    assert np.all(mask[0:10, :] == 0)
    assert np.all(mask[20:, :] == 0)
    print("  PASS\n")


def test_threshold_empty_mask():
    """Very high absolute threshold on low data should produce an empty mask."""
    print("=== Test: Empty mask from high threshold ===")
    from backend.nodes.threshold_mask import ThresholdMask
    node = ThresholdMask()

    data = np.ones((64, 64))
    field = make_field(data)

    mask, = node.process(field, method="absolute", threshold=999.0, direction="above")
    assert mask.sum() == 0, "Mask should be completely empty"
    print("  PASS\n")


def test_threshold_full_mask():
    """Very low absolute threshold should produce an all-white mask."""
    print("=== Test: Full mask from low threshold ===")
    from backend.nodes.threshold_mask import ThresholdMask
    node = ThresholdMask()

    data = np.ones((64, 64)) * 5.0
    field = make_field(data)

    mask, = node.process(field, method="absolute", threshold=-1.0, direction="above")
    assert np.all(mask == 255), "Mask should be all white"
    print("  PASS\n")


# =========================================================================
# GrainAnalysis tests
# =========================================================================

def test_single_circle_area():
    """A single filled circle — verify pixel count and physical area."""
    print("=== Test: Single circle area ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 200
    XREAL = 2e-6  # 2 µm
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)

    # Draw a filled circle, radius 30 px, centred at (100, 100)
    yy, xx = np.mgrid[0:N, 0:N]
    r = 30
    circle = ((xx - 100) ** 2 + (yy - 100) ** 2) <= r ** 2
    data[circle] = 5.0
    mask[circle] = 255

    field = make_field(data, xreal=XREAL, yreal=XREAL)
    table, = node.process(field, mask=mask, min_size=1)

    assert len(table) == 1, f"Expected 1 particles, got {len(table)}"
    particles = table[0]

    # Pixel area of a discrete circle: should be close to π r²
    expected_px = np.pi * r ** 2
    assert abs(particles["area_px"] - expected_px) / expected_px < 0.02, \
        f"area_px={particles['area_px']}, expected≈{expected_px:.0f}"

    # Physical area
    pixel_area = (XREAL / N) ** 2
    expected_m2 = particles["area_px"] * pixel_area
    assert abs(particles["area_m2"] - expected_m2) < 1e-20, \
        f"area_m2 mismatch: {particles['area_m2']} vs {expected_m2}"

    # Equivalent diameter should be close to 2r in physical units
    expected_diam = 2 * r * (XREAL / N)
    assert abs(particles["equiv_diam_m"] - expected_diam) / expected_diam < 0.02, \
        f"equiv_diam={particles['equiv_diam_m']:.3e}, expected≈{expected_diam:.3e}"

    # Heights
    assert abs(particles["mean_height"] - 5.0) < 1e-10
    assert abs(particles["max_height"] - 5.0) < 1e-10
    print("  PASS\n")


def test_multiple_particles_separation():
    """Three well-separated particles of different sizes — check each is reported."""
    print("=== Test: Multiple particles separation ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 128
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)

    # Grain A: 20×20 block, height 10
    data[10:30, 10:30] = 10.0
    mask[10:30, 10:30] = 255

    # Grain B: 10×10 block, height 7
    data[60:70, 60:70] = 7.0
    mask[60:70, 60:70] = 255

    # Grain C: 5×5 block, height 3
    data[100:105, 100:105] = 3.0
    mask[100:105, 100:105] = 255

    field = make_field(data)
    table, = node.process(field, mask=mask, min_size=1)

    assert len(table) == 3, f"Expected 3 particles, got {len(table)}"

    table.sort(key=lambda r: r["area_px"], reverse=True)
    assert table[0]["area_px"] == 400   # 20×20
    assert table[1]["area_px"] == 100   # 10×10
    assert table[2]["area_px"] == 25    # 5×5

    assert abs(table[0]["mean_height"] - 10.0) < 1e-10
    assert abs(table[1]["mean_height"] - 7.0) < 1e-10
    assert abs(table[2]["mean_height"] - 3.0) < 1e-10
    print("  PASS\n")


def test_min_size_filtering():
    """min_size should exclude particles smaller than the threshold."""
    print("=== Test: min_size filtering ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 64
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)

    # Large particles: 15×15 = 225 px
    data[5:20, 5:20] = 1.0
    mask[5:20, 5:20] = 255

    # Medium particles: 8×8 = 64 px
    data[30:38, 30:38] = 1.0
    mask[30:38, 30:38] = 255

    # Tiny particles: 3×3 = 9 px
    data[50:53, 50:53] = 1.0
    mask[50:53, 50:53] = 255

    field = make_field(data)

    # min_size=1: all three
    table, = node.process(field, mask=mask, min_size=1)
    assert len(table) == 3

    # min_size=10: drops the 3×3
    table, = node.process(field, mask=mask, min_size=10)
    assert len(table) == 2

    # min_size=100: drops the 3×3 and 8×8
    table, = node.process(field, mask=mask, min_size=100)
    assert len(table) == 1
    assert table[0]["area_px"] == 225

    # min_size=300: drops everything
    table, = node.process(field, mask=mask, min_size=300)
    assert len(table) == 0
    print("  PASS\n")


def test_particles_bounding_box():
    """Bounding box should match the particles extents."""
    print("=== Test: Grain bounding box ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 64
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)
    # Place a particles at rows 20:35, cols 10:45
    data[20:35, 10:45] = 2.0
    mask[20:35, 10:45] = 255

    field = make_field(data)
    table, = node.process(field, mask=mask, min_size=1)
    assert len(table) == 1

    bbox = table[0]["bbox"]
    # Format: "(xmin,ymin)-(xmax,ymax)" = "(10,20)-(44,34)"
    assert bbox == "(10,20)-(44,34)", f"bbox={bbox}, expected (10,20)-(44,34)"
    print("  PASS\n")


def test_empty_mask_produces_no_particles():
    """An all-zero mask should yield zero particles."""
    print("=== Test: Empty mask → no particles ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    field = make_field(np.ones((64, 64)))
    mask = np.zeros((64, 64), dtype=np.uint8)

    table, = node.process(field, mask=mask, min_size=1)
    assert len(table) == 0
    print("  PASS\n")


def test_particles_at_image_edge():
    """A particles touching the image border should still be detected."""
    print("=== Test: Grain at image edge ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 64
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)
    # Grain touching top-left corner
    data[0:10, 0:10] = 4.0
    mask[0:10, 0:10] = 255

    field = make_field(data)
    table, = node.process(field, mask=mask, min_size=1)
    assert len(table) == 1
    assert table[0]["area_px"] == 100
    assert table[0]["bbox"] == "(0,0)-(9,9)"
    print("  PASS\n")


def test_adjacent_particles_connectivity():
    """Two diagonally-touching blocks should be separate particles
    (scipy.ndimage.label uses 4-connectivity by default)."""
    print("=== Test: Diagonal adjacency → separate particles ===")
    from backend.nodes.particle_analysis import GrainAnalysis
    node = GrainAnalysis()

    N = 32
    data = np.zeros((N, N))
    mask = np.zeros((N, N), dtype=np.uint8)

    # Block A
    data[5:10, 5:10] = 1.0
    mask[5:10, 5:10] = 255

    # Block B diagonally adjacent (touching only at corner 10,10)
    data[10:15, 10:15] = 1.0
    mask[10:15, 10:15] = 255

    field = make_field(data)
    table, = node.process(field, mask=mask, min_size=1)
    # Default label() uses structure that connects diagonals? Let's verify.
    # scipy.ndimage.label default is cross-shaped (no diagonals) for 2D
    assert len(table) == 2, f"Expected 2 separate particles, got {len(table)}"
    print("  PASS\n")


# =========================================================================
# End-to-end pipeline: ThresholdMask → GrainAnalysis
# =========================================================================

def test_pipeline_synthetic():
    """Full pipeline on a synthetic image with known geometry."""
    print("=== Test: Full pipeline on synthetic particles ===")
    from backend.nodes.threshold_mask import ThresholdMask
    from backend.nodes.particle_analysis import GrainAnalysis

    N = 200
    XREAL = 10e-6  # 10 µm
    rng = np.random.default_rng(99)

    # Background at 0 with small noise, particles as raised bumps
    bg = rng.normal(0, 0.1, (N, N))
    particles = np.zeros((N, N))

    yy, xx = np.mgrid[0:N, 0:N]

    specs = [
        (50, 50, 15, 5.0),    # (cx, cy, radius_px, height)
        (150, 50, 20, 8.0),
        (100, 100, 10, 3.0),
        (50, 160, 25, 6.0),
        (160, 160, 12, 4.0),
    ]
    for cx, cy, r, h in specs:
        inside = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r ** 2
        particles[inside] = h

    data = bg + particles
    field = make_field(data, xreal=XREAL, yreal=XREAL)

    # Step 1: threshold
    thresh = ThresholdMask()
    mask, = thresh.process(field, method="absolute", threshold=1.0, direction="above")

    # Particles are well above noise, so mask should capture all 5
    assert mask.max() == 255, "No particles detected"

    # Step 2: particles analysis
    ga = GrainAnalysis()
    table, = ga.process(field, mask=mask, min_size=5)

    assert len(table) == 5, f"Expected 5 particles, got {len(table)}"

    # Verify that detected areas are in the right ballpark
    table.sort(key=lambda r: r["area_px"], reverse=True)
    expected_areas = sorted([np.pi * r ** 2 for _, _, r, _ in specs], reverse=True)

    for particles, expected_px in zip(table, expected_areas):
        ratio = particles["area_px"] / expected_px
        assert 0.85 < ratio < 1.15, \
            f"particles area_px={particles['area_px']}, expected≈{expected_px:.0f}, ratio={ratio:.2f}"

    print("  PASS\n")


def test_pipeline_demo_image():
    """Run the full pipeline on the bundled demo nanoparticles image."""
    print("=== Test: Full pipeline on demo nanoparticles.npy ===")
    from pathlib import Path
    from backend.nodes.threshold_mask import ThresholdMask
    from backend.nodes.particle_analysis import GrainAnalysis
    from backend.runtime_paths import demo_dir

    npy_path = demo_dir() / "nanoparticles.npy"
    if not npy_path.exists():
        print("  SKIP (demo image not found)\n")
        return

    data = np.load(str(npy_path)).astype(np.float64)
    # The demo image is a 5 µm × 5 µm scan
    field = make_field(data, xreal=5e-6, yreal=5e-6)

    # Threshold to find particles (they are raised above background)
    thresh = ThresholdMask()
    mask, = thresh.process(field, method="otsu", threshold=0.0, direction="above")

    # Should detect particles
    assert mask.max() == 255, "No particles found in demo image"
    particle_fraction = (mask == 255).sum() / mask.size
    assert 0.01 < particle_fraction < 0.5, \
        f"Suspicious particle fraction: {particle_fraction:.3f}"
    print(f"  Mask: {particle_fraction*100:.1f}% of pixels are particles")

    # Grain analysis
    ga = GrainAnalysis()
    table, = ga.process(field, mask=mask, min_size=20)

    assert len(table) > 0, "No particles detected"
    print(f"  Found {len(table)} particles (min_size=20)")

    # Sanity checks on particles properties
    for particles in table:
        assert particles["area_px"] >= 20
        assert particles["area_m2"] > 0
        assert particles["equiv_diam_m"] > 0
        assert particles["max_height"] >= particles["mean_height"]
        assert particles["mean_height"] > 0

    # Physical size sanity: equivalent diameters should be in the nm–µm range
    diams_nm = [g["equiv_diam_m"] * 1e9 for g in table]
    print(f"  Diameters: min={min(diams_nm):.0f} nm, max={max(diams_nm):.0f} nm")
    assert all(1 < d < 2000 for d in diams_nm), \
        f"Grain diameters out of expected range: {diams_nm}"

    print("  PASS\n")


# =========================================================================
# Run all tests
# =========================================================================

if __name__ == "__main__":
    # ThresholdMask
    test_threshold_otsu_bimodal()
    test_threshold_relative_range()
    test_threshold_empty_mask()
    test_threshold_full_mask()

    # GrainAnalysis
    test_single_circle_area()
    test_multiple_particles_separation()
    test_min_size_filtering()
    test_particles_bounding_box()
    test_empty_mask_produces_no_particles()
    test_particles_at_image_edge()
    test_adjacent_particles_connectivity()

    # End-to-end pipeline
    test_pipeline_synthetic()
    test_pipeline_demo_image()

    print("All particles tests passed!")
