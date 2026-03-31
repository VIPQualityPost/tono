import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_entropy_uniform_field_low():
    """A field with a single unique value has zero entropy."""
    from backend.nodes.entropy import Entropy

    node = Entropy()
    field = make_field(data=np.full((32, 32), 3.14))
    h, h_norm = node.process(field, mode="height values", n_bins=256)
    # All values fall in one bin → p=1 → H = 0
    assert h == pytest.approx(0.0, abs=1e-10)
    assert h_norm == pytest.approx(0.0, abs=1e-10)


def test_entropy_random_field_positive():
    """A random field should have positive entropy."""
    from backend.nodes.entropy import Entropy

    rng = np.random.default_rng(0)
    field = make_field(data=rng.standard_normal((64, 64)))
    node = Entropy()
    h, h_norm = node.process(field, mode="height values", n_bins=256)
    assert h > 0.0
    assert 0.0 < h_norm <= 1.0


def test_entropy_normalised_leq_one():
    """Normalised entropy should never exceed 1."""
    from backend.nodes.entropy import Entropy

    rng = np.random.default_rng(2)
    field = make_field(data=rng.uniform(0, 1, (64, 64)))
    node = Entropy()
    _, h_norm = node.process(field, mode="height values", n_bins=64)
    assert h_norm <= 1.0 + 1e-12


def test_entropy_slope_mode():
    """Slope mode should work and return valid entropy values."""
    from backend.nodes.entropy import Entropy

    rng = np.random.default_rng(3)
    field = make_field(data=rng.standard_normal((32, 32)))
    node = Entropy()
    h, h_norm = node.process(field, mode="slope magnitude", n_bins=128)
    assert h > 0.0
    assert 0.0 <= h_norm <= 1.0


def test_entropy_more_uniform_is_higher():
    """Uniformly distributed values have higher entropy than a spiked distribution."""
    from backend.nodes.entropy import Entropy

    rng = np.random.default_rng(4)
    uniform = rng.uniform(0, 1, (64, 64))
    spiked = np.zeros((64, 64))
    spiked[0, 0] = 1.0

    node = Entropy()
    h_uniform, _ = node.process(make_field(data=uniform), mode="height values", n_bins=64)
    h_spiked, _ = node.process(make_field(data=spiked), mode="height values", n_bins=64)
    assert h_uniform > h_spiked


def test_entropy_returns_floats():
    from backend.nodes.entropy import Entropy

    field = make_field()
    node = Entropy()
    h, h_norm = node.process(field, mode="height values", n_bins=256)
    assert isinstance(h, float)
    assert isinstance(h_norm, float)
