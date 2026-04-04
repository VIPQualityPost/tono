import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shapes():
    from backend.nodes.mfm_domains import MFMDomainGeneration

    node = MFMDomainGeneration()
    field = make_field(shape=(48, 64))

    hz, dhz_dz = node.process(
        field,
        height=50e-9,
        thickness=20e-9,
        magnetization=1e6,
        stripe_width_a=200e-9,
        stripe_width_b=200e-9,
        gap=0.0,
    )
    assert hz.data.shape == (48, 64)
    assert dhz_dz.data.shape == (48, 64)


def test_finite_values():
    from backend.nodes.mfm_domains import MFMDomainGeneration

    node = MFMDomainGeneration()
    field = make_field(shape=(32, 32))

    hz, dhz_dz = node.process(
        field,
        height=50e-9,
        thickness=20e-9,
        magnetization=1e6,
        stripe_width_a=200e-9,
        stripe_width_b=200e-9,
        gap=0.0,
    )
    assert np.isfinite(hz.data).all()
    assert np.isfinite(dhz_dz.data).all()


def test_uniform_along_y():
    """Stripes run along y, so every row of the output should be identical."""
    from backend.nodes.mfm_domains import MFMDomainGeneration

    node = MFMDomainGeneration()
    field = make_field(shape=(64, 64))

    hz, dhz_dz = node.process(
        field,
        height=50e-9,
        thickness=20e-9,
        magnetization=1e6,
        stripe_width_a=200e-9,
        stripe_width_b=200e-9,
        gap=0.0,
    )
    assert np.allclose(hz.data[0], hz.data[hz.data.shape[0] // 2])
    assert np.allclose(dhz_dz.data[0], dhz_dz.data[dhz_dz.data.shape[0] // 2])


def test_units():
    from backend.nodes.mfm_domains import MFMDomainGeneration

    node = MFMDomainGeneration()
    field = make_field(shape=(32, 32))

    hz, dhz_dz = node.process(
        field,
        height=50e-9,
        thickness=20e-9,
        magnetization=1e6,
        stripe_width_a=200e-9,
        stripe_width_b=200e-9,
        gap=0.0,
    )
    assert hz.si_unit_z == "A/m"
    assert dhz_dz.si_unit_z == "A/m²"
