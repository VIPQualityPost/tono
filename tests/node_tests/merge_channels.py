import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _ramp_field(shape=(16, 16), start=0.0, stop=1.0):
    return make_field(data=np.linspace(start, stop, shape[0] * shape[1]).reshape(shape))


def test_merge_output_arity():
    """The node returns exactly one output matching its OUTPUTS tuple."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    field = _ramp_field()
    result = node.process(field, field, field, scaling="auto", offset=0.0, scale=1.0)
    assert len(result) == len(MergeChannels.OUTPUTS) == 1
    image = result[0]
    assert image.dtype == np.uint8
    assert image.shape == (16, 16, 3)


def test_merge_auto_scaling_channels():
    """Auto mode stretches each channel's full range to 0..255 and maps the
    channel order red/green/blue correctly."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    h, w = 8, 8
    red = make_field(data=np.zeros((h, w)))            # flat 0 -> 0
    green = _ramp_field(shape=(h, w), start=0.0, stop=1.0)  # 0..1 -> 0..255
    blue = make_field(data=np.ones((h, w)))            # flat 1 -> 0 (flat spans no range)
    (image,) = node.process(red, green, blue, scaling="auto", offset=0.0, scale=1.0)

    assert image.shape == (h, w, 3)
    assert image[..., 0].min() == 0 and image[..., 0].max() == 0
    # green: first pixel 0, last pixel 255, monotonically increasing
    assert image[0, 0, 1] == 0
    assert image[-1, -1, 1] == 255
    assert np.all(np.diff(image[..., 1].ravel()) >= 0)
    # linear ramp: centre pixel (row 4, col 0) -> index 32 of 64 -> 32/63
    mid = image[h // 2, 0, 1]
    assert int(mid) == int(np.round(255.0 * (32.0 / 63.0)))  # = 130


def test_merge_manual_scaling():
    """Manual mode maps (value - offset)/scale to 0..255 with clipping."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    data = np.array([[0.0, 1.0, 2.0, 3.0, 4.0]])
    field = make_field(data=data)
    (image,) = node.process(field, field, field, scaling="manual", offset=0.0, scale=2.0)

    # At most 5 unique values per channel: 0, 0.5, 1 -> clip at 1 -> 0..255
    channel = image[0, :, 0].astype(np.float64) / 255.0
    # values 0, 1, 2, 3, 4 -> normalized 0, 0.5, 1, 1, 1
    expected_norm = np.array([0.0, 0.5, 1.0, 1.0, 1.0])
    assert np.allclose(channel, expected_norm, atol=1.0 / 255.0 + 1e-9)
    # symmetry across channels
    np.testing.assert_array_equal(image[..., 0], image[..., 1])
    np.testing.assert_array_equal(image[..., 1], image[..., 2])


def test_merge_flat_field_auto_is_black():
    """A flat channel has no range, so auto mode maps it entirely to 0."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    field = make_field(data=np.full((8, 8), 3.0))
    (image,) = node.process(field, field, field, scaling="auto", offset=0.0, scale=1.0)
    assert image.min() == 0 and image.max() == 0


def test_merge_shape_mismatch_raises():
    """Incompatible channel resolutions raise a ValueError."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    a = make_field(data=np.zeros((8, 8)))
    b = make_field(data=np.zeros((16, 16)))
    with pytest.raises(ValueError):
        node.process(a, b, a, scaling="auto", offset=0.0, scale=1.0)
    with pytest.raises(ValueError):
        node.process(a, a, b, scaling="auto", offset=0.0, scale=1.0)


def test_merge_manual_nonpositive_scale_raises():
    """Manual mode rejects a non-positive scale."""
    from backend.nodes.merge_channels import MergeChannels

    node = MergeChannels()
    field = _ramp_field()
    with pytest.raises(ValueError):
        node.process(field, field, field, scaling="manual", offset=0.0, scale=0.0)
    with pytest.raises(ValueError):
        node.process(field, field, field, scaling="manual", offset=0.0, scale=-1.0)
