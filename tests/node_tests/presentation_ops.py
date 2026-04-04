import numpy as np
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.presentation_ops import PresentationOps

    node = PresentationOps()
    field = make_field(shape=(32, 32))
    result, = node.process(field, "logscale", blend_factor=0.5)
    assert result.data.shape == field.data.shape


def test_logscale():
    from backend.nodes.presentation_ops import PresentationOps

    node = PresentationOps()
    data = np.array([[1.0, 10.0], [100.0, 1000.0]])
    field = make_field(data=data)
    result, = node.process(field, "logscale", blend_factor=0.5)
    assert np.all(np.isfinite(result.data))
    # logscale should preserve ordering
    assert result.data[0, 0] < result.data[0, 1] < result.data[1, 0] < result.data[1, 1]


def test_blend_at_zero():
    from backend.nodes.presentation_ops import PresentationOps

    node = PresentationOps()
    field = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))
    overlay = make_field(data=np.array([[10.0, 20.0], [30.0, 40.0]]))
    result, = node.process(field, "blend", blend_factor=0.0, overlay=overlay)
    assert np.allclose(result.data, field.data)


def test_blend_at_one():
    from backend.nodes.presentation_ops import PresentationOps

    node = PresentationOps()
    field = make_field(data=np.array([[1.0, 2.0], [3.0, 4.0]]))
    overlay = make_field(data=np.array([[10.0, 20.0], [30.0, 40.0]]))
    result, = node.process(field, "blend", blend_factor=1.0, overlay=overlay)
    assert np.allclose(result.data, overlay.data)
