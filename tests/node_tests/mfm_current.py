import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shapes():
    from backend.nodes.mfm_current import MFMCurrentSimulation

    node = MFMCurrentSimulation()
    field = make_field(shape=(32, 32))

    hx, hz, force = node.process(field, height=100e-9, current=1e-3,
                                 width=100e-9, tip_magnetization=1e5)

    assert hx.data.shape == (32, 32)
    assert hz.data.shape == (32, 32)
    assert force.data.shape == (32, 32)


def test_finite_values():
    from backend.nodes.mfm_current import MFMCurrentSimulation

    node = MFMCurrentSimulation()
    field = make_field(shape=(64, 64))

    hx, hz, force = node.process(field, height=100e-9, current=1e-3,
                                 width=100e-9, tip_magnetization=1e5)

    assert np.isfinite(hx.data).all()
    assert np.isfinite(hz.data).all()
    assert np.isfinite(force.data).all()


def test_hz_antisymmetric():
    from backend.nodes.mfm_current import MFMCurrentSimulation

    node = MFMCurrentSimulation()
    # Use even grid so centre falls between pixels symmetrically
    field = make_field(shape=(16, 64), xreal=1e-6, yreal=1e-6)

    _, hz, _ = node.process(field, height=100e-9, current=1e-3,
                            width=100e-9, tip_magnetization=1e5)

    hz_row = hz.data[0, :]
    n = len(hz_row)
    # The x-grid uses linspace(0, xreal, n, endpoint=False) - xreal/2,
    # so x[i] + x[n-i] == 0 for i in 1..n-1.
    # Hz should be antisymmetric about x=0: Hz(x) ≈ -Hz(-x)
    for i in range(1, n // 2):
        left = hz_row[i]
        right = hz_row[n - i]
        assert np.sign(left) == -np.sign(right), (
            f"Hz not antisymmetric at positions {i} and {n - i}: "
            f"{left} vs {right}"
        )
        np.testing.assert_allclose(left, -right, rtol=1e-10)


def test_units():
    from backend.nodes.mfm_current import MFMCurrentSimulation

    node = MFMCurrentSimulation()
    field = make_field(shape=(32, 32))

    hx, hz, force = node.process(field, height=100e-9, current=1e-3,
                                 width=100e-9, tip_magnetization=1e5)

    assert hx.si_unit_z == "A/m"
    assert hz.si_unit_z == "A/m"
    assert force.si_unit_z == "N"
