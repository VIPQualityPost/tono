import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_custom_convolution_identity_kernel():
    """[[1]] with normalize=True (abs_sum=1) should return input unchanged."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    data = np.random.default_rng(0).standard_normal((32, 32))
    field = make_field(data=data)
    result, = node.process(field, kernel="1", normalize=False, boundary="reflect")
    assert np.allclose(result.data, data)


def test_custom_convolution_uniform_kernel_normalized():
    """An all-ones kernel with normalize=True is a box filter (mean filter)."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    data = np.random.default_rng(1).standard_normal((32, 32))
    field = make_field(data=data)
    # 3x3 all-ones kernel, normalized → each pixel becomes mean of its neighbourhood
    kernel = "1 1 1\n1 1 1\n1 1 1"
    result, = node.process(field, kernel=kernel, normalize=True, boundary="reflect")
    # Output std should be less than input std (smoothing)
    assert result.data.std() < data.std()


def test_custom_convolution_sharpen_increases_variation():
    """A sharpening kernel should increase local variation on a smooth field."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    # Smooth ramp field — very low frequency content
    data = np.outer(np.linspace(0, 1, 32), np.linspace(0, 1, 32))
    field = make_field(data=data)
    sharpen = "0 -1 0\n-1 5 -1\n0 -1 0"
    result, = node.process(field, kernel=sharpen, normalize=False, boundary="reflect")
    # Sharpening without normalisation keeps the ramp intact plus adds edges
    # The std of the sharpened field should differ from input
    assert result.data.std() != pytest.approx(data.std(), rel=0.0)


def test_custom_convolution_shape_preserved():
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    field = make_field(shape=(48, 64))
    result, = node.process(field, kernel="0 1 0\n1 1 1\n0 1 0", normalize=True, boundary="reflect")
    assert result.data.shape == (48, 64)


def test_custom_convolution_invalid_kernel_fallback():
    """An invalid kernel string should return the input field unchanged."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    data = np.random.default_rng(2).standard_normal((16, 16))
    field = make_field(data=data)
    result, = node.process(field, kernel="", normalize=True, boundary="reflect")
    assert np.allclose(result.data, data)


def test_custom_convolution_ragged_kernel_fallback():
    """A ragged (non-rectangular) kernel should be rejected gracefully."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    data = np.random.default_rng(3).standard_normal((16, 16))
    field = make_field(data=data)
    result, = node.process(field, kernel="1 2\n1 2 3", normalize=True, boundary="reflect")
    assert np.allclose(result.data, data)


def test_custom_convolution_boundary_modes():
    """All boundary modes should produce valid output without error."""
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    field = make_field()
    for mode in ("reflect", "nearest", "wrap"):
        result, = node.process(field, kernel="1 1 1\n1 1 1\n1 1 1", normalize=True, boundary=mode)
        assert result.data.shape == field.data.shape


def test_custom_convolution_preserves_metadata():
    from backend.nodes.filter_custom import CustomConvolution

    node = CustomConvolution()
    field = make_field()
    result, = node.process(field, kernel="1", normalize=False, boundary="reflect")
    assert result.xreal == field.xreal
    assert result.si_unit_z == field.si_unit_z
