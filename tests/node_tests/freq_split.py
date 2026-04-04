import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_sum_reconstruction():
    """Low-pass plus high-pass should reconstruct the original field."""
    from backend.nodes.freq_split import FrequencySplit

    node = FrequencySplit()
    field = make_field(shape=(64, 64))
    low, high = node.process(field, cutoff=0.1)
    reconstructed = low.data + high.data
    assert np.allclose(reconstructed, field.data, atol=1e-10)


def test_shapes():
    """Both outputs should have the same shape as the input."""
    from backend.nodes.freq_split import FrequencySplit

    node = FrequencySplit()
    field = make_field(shape=(64, 64))
    low, high = node.process(field, cutoff=0.1)
    assert low.data.shape == field.data.shape
    assert high.data.shape == field.data.shape


def test_low_pass_smoother():
    """Low-pass output should have smaller std than the original random data."""
    from backend.nodes.freq_split import FrequencySplit

    node = FrequencySplit()
    field = make_field(shape=(64, 64))
    low, high = node.process(field, cutoff=0.1)
    assert np.std(low.data) < np.std(field.data)
