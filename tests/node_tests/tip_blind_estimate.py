import numpy as np
import pytest
from tests.node_tests._shared import make_field
from backend.data_types import DataField


def run_blind(field, n_pixels=17, threshold=0.0, method="partial", use_edges=False):
    from backend.nodes.tip_blind_estimate import BlindTipEstimate
    node = BlindTipEstimate()
    tip, certainty = node.process(
        field=field, n_pixels=n_pixels, threshold=threshold,
        method=method, use_edges=use_edges,
    )
    return tip, certainty


# ── Output types and dimensions ──────────────────────────────────────────────

def test_outputs_are_data_fields():
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    tip, certainty = run_blind(field, n_pixels=9)
    assert isinstance(tip, DataField)
    assert isinstance(certainty, DataField)


def test_tip_output_shape():
    """Tip must be (n_pixels, n_pixels) — odd, bumped if even."""
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    for n in (7, 11, 17):
        tip, _ = run_blind(field, n_pixels=n)
        assert tip.data.shape == (n, n), f"Expected ({n},{n}), got {tip.data.shape}"


def test_tip_n_pixels_even_bumped():
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    tip, _ = run_blind(field, n_pixels=16)
    assert tip.data.shape[0] == 17


def test_certainty_output_matches_field_shape():
    field = make_field(shape=(48, 64))
    _, certainty = run_blind(field, n_pixels=9)
    assert certainty.data.shape == field.data.shape


def test_certainty_is_binary():
    """Certainty map values must all be 0.0 or 1.0."""
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    _, certainty = run_blind(field, n_pixels=9)
    vals = np.unique(certainty.data)
    for v in vals:
        assert v in (0.0, 1.0), f"Non-binary certainty value: {v}"


# ── Tip conventions ───────────────────────────────────────────────────────────

def test_tip_min_is_zero():
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    tip, _ = run_blind(field, n_pixels=9)
    assert tip.data.min() >= -1e-15


def test_tip_max_at_centre():
    """Apex (centre pixel) must be the maximum of the estimated tip."""
    field = make_field(shape=(32, 32), xreal=32e-9, yreal=32e-9)
    tip, _ = run_blind(field, n_pixels=9)
    ci = tip.data.shape[0] // 2
    assert tip.data[ci, ci] == pytest.approx(tip.data.max(), abs=1e-20)


def test_tip_units_inherited():
    field = make_field(xreal=1e-6, yreal=1e-6)
    field.si_unit_xy = "nm"
    field.si_unit_z = "V"
    tip, _ = run_blind(field, n_pixels=9)
    assert tip.si_unit_xy == "nm"
    assert tip.si_unit_z == "V"


# ── Flat field gives flat (zero) tip ─────────────────────────────────────────

def test_flat_field_gives_zero_tip():
    """A flat image has no features → blind estimation cannot refine the tip → stays flat."""
    flat = make_field(data=np.full((32, 32), 3.14))
    tip, _ = run_blind(flat, n_pixels=7)
    # Tip should be all zeros (no refinement possible)
    assert np.allclose(tip.data, 0.0, atol=1e-12)


# ── Single spike → estimated tip matches expected shape ──────────────────────

def test_spike_gives_sharp_tip():
    """
    A single sharp spike dilated by a known paraboloid tip gives a broadened image.
    Blind estimation on the broadened image should recover a tip that is ≤ the true tip
    everywhere (blind estimation is an upper bound on the true tip shape).
    """
    from scipy.ndimage import grey_dilation
    from backend.nodes.tip_model import TipModel

    pixel_size = 1e-9
    n = 64
    field_ref = make_field(shape=(n, n), xreal=n * pixel_size, yreal=n * pixel_size)

    # Create true parabolic tip (33×33, radius=20nm)
    true_tip_node = TipModel()
    true_tip, = true_tip_node.process(
        field=field_ref, shape="parabola", radius=20e-9,
        half_angle=20.0, n_pixels=33,
    )

    # Spike surface
    surface = np.zeros((n, n))
    surface[n // 2, n // 2] = 1e-9   # 1 nm spike

    # Dilated (measured) image
    dil_struct = true_tip.data - true_tip.data.max()
    measured_data = grey_dilation(surface, structure=dil_struct)
    measured = make_field(data=measured_data, xreal=n * pixel_size, yreal=n * pixel_size)

    # Blind estimation
    est_tip, certainty = run_blind(measured, n_pixels=33, threshold=0.0, method="partial")

    # The estimated tip must be ≤ the true tip everywhere (blind est. is upper bound)
    # Both are min=0, max=apex. Compare normalised shapes.
    true_norm = true_tip.data / true_tip.data.max() if true_tip.data.max() > 0 else true_tip.data
    est_norm = est_tip.data / est_tip.data.max() if est_tip.data.max() > 0 else est_tip.data
    # After normalisation: est ≤ true everywhere (blind is conservative)
    assert np.all(est_norm <= true_norm + 1e-6), \
        "Blind estimate exceeded true tip (not a valid upper bound)"


# ── Partial vs full ───────────────────────────────────────────────────────────

def test_full_method_runs():
    """Full estimation should run without error on a small image."""
    field = make_field(shape=(24, 24), xreal=24e-9, yreal=24e-9)
    tip, certainty = run_blind(field, n_pixels=7, method="full")
    assert isinstance(tip, DataField)
    assert isinstance(certainty, DataField)


# ── Certainty increases with sharp features ───────────────────────────────────

def test_certainty_nonzero_for_sharp_image():
    """An image with distinct features should produce some certain pixels."""
    from scipy.ndimage import grey_dilation
    from backend.nodes.tip_model import TipModel

    pixel_size = 1e-9
    n = 64
    field_ref = make_field(shape=(n, n), xreal=n * pixel_size, yreal=n * pixel_size)
    true_tip_node = TipModel()
    true_tip, = true_tip_node.process(
        field=field_ref, shape="parabola", radius=20e-9,
        half_angle=20.0, n_pixels=17,
    )

    # Create a sharp pyramid surface
    cx, cy = n // 2, n // 2
    ys, xs = np.mgrid[0:n, 0:n]
    surface = np.maximum(0, 5e-9 - 0.3e-9 * np.maximum(np.abs(xs - cx), np.abs(ys - cy)))
    dil_struct = true_tip.data - true_tip.data.max()
    measured_data = grey_dilation(surface, structure=dil_struct)
    measured = make_field(data=measured_data, xreal=n * pixel_size, yreal=n * pixel_size)

    _, certainty = run_blind(measured, n_pixels=17, method="partial")
    assert certainty.data.sum() > 0, "No certain pixels found for a sharp image"
