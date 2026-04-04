import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_lattice_acf_returns_outputs():
    from backend.nodes.lattice_measurement import LatticeMeasurement

    node = LatticeMeasurement()
    field = make_field(shape=(64, 64))
    corr, records = node.process(field, "acf")
    assert corr.data.shape == (64, 64)
    assert isinstance(records, list)


def test_lattice_fft_returns_outputs():
    from backend.nodes.lattice_measurement import LatticeMeasurement

    node = LatticeMeasurement()
    field = make_field(shape=(64, 64))
    corr, records = node.process(field, "fft")
    assert corr.data.shape == (64, 64)


def test_lattice_detects_periodic_structure():
    """A simple cosine grid should produce lattice measurements."""
    from backend.nodes.lattice_measurement import LatticeMeasurement

    node = LatticeMeasurement()
    x = np.linspace(0, 4 * np.pi, 64, endpoint=False)
    X, Y = np.meshgrid(x, x)
    data = np.cos(X) + np.cos(Y)
    field = make_field(data=data)

    corr, records = node.process(field, "acf")
    # Should detect at least one vector
    assert len(records) >= 3


def test_lattice_unknown_method():
    from backend.nodes.lattice_measurement import LatticeMeasurement

    node = LatticeMeasurement()
    field = make_field(shape=(32, 32))
    with pytest.raises(ValueError):
        node.process(field, "unknown")
