import numpy as np
import pytest
from tests.node_tests._shared import make_field


@pytest.fixture(scope="module")
def node():
    from backend.nodes.mfm_parallel_media import MFMParallelMedia

    return MFMParallelMedia()


@pytest.fixture(scope="module")
def params():
    # dx = dy = 10 nm so a 400 nm stripe period is exactly 40 px and a half
    # period (200 nm) exactly 20 px.
    field = make_field(shape=(64, 128), xreal=1.28e-6, yreal=1.28e-6)
    return {
        "field": field,
        "probe": "point_charge",
        "height": 100e-9,
        "thickness": 20e-9,
        "magnetization": 1e6,
        "size_a": 200e-9,
        "size_b": 200e-9,
        "size_c": 0.0,
        "mtip": 1e3,
        "bx": 10e-9,
        "by": 10e-9,
        "length": 500e-9,
    }


def test_output_arity_and_shape(node, params):
    for operation in ("hx", "hz", "force", "force_dz", "force_ddz"):
        out = node.process(operation=operation, **params)
        assert isinstance(out, tuple) and len(out) == 1
        assert out[0].data.shape == params["field"].data.shape


def test_finite_values(node, params):
    for operation in ("hx", "hz", "force", "force_dz", "force_ddz"):
        (out,) = node.process(operation=operation, **params)
        assert np.isfinite(out.data).all()


def test_uniform_along_y(node, params):
    """The stripes and gaps run along y, so every output row is identical."""
    (out,) = node.process(operation="hz", **params)
    assert np.allclose(out.data[0], out.data[out.data.shape[0] // 2])


def test_hz_periodicity_and_half_period_antisymmetry(node, params):
    """For equal stripe widths and no gaps the medium is periodic with period
    p = 2a and its stray field satisfies hz(x) = hz(x + p) and (with a small
    truncation error from the finite boundary list)
    hz(x + p/2) = -hz(x)."""
    (out,) = node.process(operation="hz", **params)
    row = out.data[0]
    n = 128 - 40  # 40 px = full period, 20 px = half period
    assert np.allclose(row[40:], row[:n], atol=1e-6)
    scale = np.abs(row).max()
    assert np.abs(row[20:] + row[:108]).max() < 5e-2 * scale


def test_hx_half_period_antisymmetry(node, params):
    (out,) = node.process(operation="hx", **params)
    row = out.data[0]
    scale = np.abs(row).max()
    assert np.abs(row[20:] + row[:108]).max() < 5e-2 * scale


def test_linearity_in_magnetization(node, params):
    """All field components are linear in the remanent magnetisation."""
    base = node.process(operation="hz", **params)[0]
    double = node.process(operation="hz", **dict(params, magnetization=2e6))[0]
    assert np.allclose(double.data, 2.0 * base.data, rtol=1e-12, atol=1e-12)


def test_point_charge_force_is_scaled_hz(node, params):
    """For the point-charge probe Fz = -mu0*mtip*bx*by * Hz exactly
    (constant transfer function in Fourier space)."""
    from backend.nodes.mfm_parallel_media import MU_0

    hz = node.process(operation="hz", **params)[0].data
    fz = node.process(operation="force", **params)[0].data
    c = -MU_0 * params["mtip"] * params["bx"] * params["by"]
    assert np.allclose(fz, c * hz, rtol=1e-10, atol=1e-12)


def test_higher_lift_decays_field(node, params):
    """Moving the output plane away from the surface must attenuate the field."""
    low = node.process(operation="hx", **dict(params, height=50e-9))[0]
    high = node.process(operation="hx", **dict(params, height=500e-9))[0]
    assert np.abs(high.data).max() < np.abs(low.data).max()


def test_units(node, params):
    from backend.nodes.mfm_parallel_media import MFMParallelMedia

    cases = [
        ("hx", "A/m"),
        ("hz", "A/m"),
        ("force", "N"),
        ("force_dz", "N/m"),
        ("force_ddz", "N/m²"),
    ]
    for operation, unit in cases:
        (out,) = node.process(operation=operation, **params)
        assert out.si_unit_z == unit
    # Lateral geometry is preserved.
    (out,) = node.process(operation="hz", **params)
    assert out.xreal == params["field"].xreal
    assert out.yreal == params["field"].yreal
    assert out.si_unit_xy == params["field"].si_unit_xy


def test_unknown_operation_and_probe_raise(node, params):
    from backend.nodes.mfm_parallel_media import MFMParallelMedia

    with pytest.raises(ValueError):
        node.process(operation="bogus", **params)
    bad_probe = dict(params)
    bad_probe["probe"] = "bogus"
    with pytest.raises(ValueError):
        node.process(operation="force", **bad_probe)
