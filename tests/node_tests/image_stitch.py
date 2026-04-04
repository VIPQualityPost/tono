import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_stitch_right_no_overlap():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.ones((32, 32)))
    b = make_field(data=np.ones((32, 32)) * 2)
    result, = node.process(a, b, "right", "none")
    assert result.data.shape[0] == 32
    assert result.data.shape[1] >= 32


def test_stitch_below():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.ones((32, 32)))
    b = make_field(data=np.ones((32, 32)) * 2)
    result, = node.process(a, b, "below", "none")
    assert result.data.shape[1] == 32
    assert result.data.shape[0] >= 32


def test_stitch_auto_direction():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(data=np.random.default_rng(0).standard_normal((32, 32)))
    b = make_field(data=np.random.default_rng(1).standard_normal((32, 32)))
    result, = node.process(a, b, "auto", "linear")
    assert result.data.ndim == 2


def test_stitch_unknown_direction():
    from backend.nodes.image_stitch import ImageStitch

    node = ImageStitch()
    a = make_field(shape=(16, 16))
    b = make_field(shape=(16, 16))
    with pytest.raises(ValueError):
        node.process(a, b, "unknown", "none")
