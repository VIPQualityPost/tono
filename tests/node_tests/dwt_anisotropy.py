import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    """Anisotropy map shape must match the input field."""
    from backend.nodes.dwt_anisotropy import DWTAnisotropy

    node = DWTAnisotropy()
    field = make_field(shape=(64, 64))
    aniso_field, stats = node.process(field, n_levels=4, ratio_threshold=0.2)
    assert aniso_field.data.shape == (64, 64)
    # Statistics rows conform to {quantity, value, unit}: four rows per level.
    assert len(stats) == 4 * 4
    assert all(set(row) == {"quantity", "value", "unit"} for row in stats)


def test_isotropic_surface():
    """A random isotropic surface should have X/Y energy ratios near 1.0."""
    from backend.nodes.dwt_anisotropy import DWTAnisotropy

    rng = np.random.default_rng(42)
    # Use a larger field so deeper levels still have enough coefficients
    data = rng.standard_normal((128, 128))
    field = make_field(data=data)
    node = DWTAnisotropy()
    aniso_field, stats = node.process(field, n_levels=3, ratio_threshold=0.2)

    ratios = {
        row["quantity"]: row["value"]
        for row in stats
        if row["quantity"].endswith("X/Y ratio")
    }
    for level in range(1, 4):
        ratio = ratios[f"Level {level} X/Y ratio"]
        assert 0.5 < ratio < 2.0, (
            f"Level {level} ratio {ratio:.3f} too far from 1.0 for isotropic surface"
        )


def test_statistics_table():
    """Statistics output is a list of dicts with the expected keys."""
    from backend.nodes.dwt_anisotropy import DWTAnisotropy

    node = DWTAnisotropy()
    field = make_field(shape=(64, 64))
    aniso_field, stats = node.process(field, n_levels=3, ratio_threshold=0.2)

    assert isinstance(stats, list)
    assert len(stats) == 4 * 3  # X/Y energy, X/Y ratio, anisotropic flag per level
    expected_keys = {"quantity", "value", "unit"}
    expected_quantities = {
        f"Level {level} {kind}"
        for level in range(1, 4)
        for kind in ("X energy", "Y energy", "X/Y ratio", "anisotropic")
    }
    assert {row["quantity"] for row in stats} == expected_quantities
    for row in stats:
        assert isinstance(row, dict)
        assert set(row.keys()) == expected_keys
        assert isinstance(row["value"], float)


def test_anisotropic_detection():
    """Horizontal stripes should produce a ratio clearly different from 1.0."""
    from backend.nodes.dwt_anisotropy import DWTAnisotropy

    # Create horizontal stripes: constant along columns, varying along rows
    data = np.tile(np.sin(np.linspace(0, 10 * np.pi, 64)), (64, 1))
    field = make_field(data=data)
    node = DWTAnisotropy()
    aniso_field, stats = node.process(field, n_levels=4, ratio_threshold=0.2)

    # At least one level should show a ratio far from 1.0
    ratios = [row["value"] for row in stats if row["quantity"].endswith("X/Y ratio")]
    flags = [row["value"] for row in stats if row["quantity"].endswith("anisotropic")]
    has_anisotropic = any(abs(ratio - 1.0) > 0.2 for ratio in ratios)
    assert has_anisotropic, (
        f"Expected anisotropic detection for horizontal stripes, ratios: {ratios}"
    )
    # The anisotropic flag must agree: at least one level flagged.
    assert any(flag == 1.0 for flag in flags)
