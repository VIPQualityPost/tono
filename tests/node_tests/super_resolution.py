import numpy as np
from tests.node_tests._shared import make_field


def test_output_shape_single():
    """Single input with upscale=2 gives 2x output size."""
    from backend.nodes.super_resolution import SuperResolution

    field = make_field(shape=(32, 32))
    node = SuperResolution()
    result, = node.process(field, upscale=2)
    assert result.data.shape == (64, 64)


def test_output_shape_multi():
    """Multiple inputs still give 2x output size."""
    from backend.nodes.super_resolution import SuperResolution

    rng = np.random.default_rng(0)
    f1 = make_field(data=rng.standard_normal((32, 32)))
    f2 = make_field(data=rng.standard_normal((32, 32)))
    f3 = make_field(data=rng.standard_normal((32, 32)))
    node = SuperResolution()
    result, = node.process(f1, upscale=2, field2=f2, field3=f3)
    assert result.data.shape == (64, 64)


def test_finite_values():
    """Output values must all be finite."""
    from backend.nodes.super_resolution import SuperResolution

    rng = np.random.default_rng(1)
    f1 = make_field(data=rng.standard_normal((32, 32)))
    f2 = make_field(data=rng.standard_normal((32, 32)))
    node = SuperResolution()
    result, = node.process(f1, upscale=2, field2=f2)
    assert np.all(np.isfinite(result.data))


def test_upscale_factor():
    """Output dimensions should equal input dimensions times upscale factor."""
    from backend.nodes.super_resolution import SuperResolution

    field = make_field(shape=(32, 32))
    node = SuperResolution()
    for factor in (2, 3, 4):
        result, = node.process(field, upscale=factor)
        expected = (32 * factor, 32 * factor)
        assert result.data.shape == expected, (
            f"upscale={factor}: expected {expected}, got {result.data.shape}"
        )
