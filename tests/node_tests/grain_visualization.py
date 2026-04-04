import numpy as np
from tests.node_tests._shared import make_field


def _make_test_inputs():
    """Create a 64x64 field and mask with two isolated blobs."""
    data = np.zeros((64, 64), dtype=np.float64)
    data[10:20, 10:20] = 5.0
    data[40:55, 40:55] = 3.0
    field = make_field(data=data, xreal=1e-6, yreal=1e-6)

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    mask[40:55, 40:55] = 255
    return field, mask


def test_output_shape():
    from backend.nodes.grain_visualization import GrainVisualization

    node = GrainVisualization()
    field, mask = _make_test_inputs()
    result, labeled = node.process(field, mask, style="inscribed_disc", fill=False)
    assert result.shape == mask.shape, (
        f"Result shape {result.shape} does not match input shape {mask.shape}"
    )


def test_labeled_grains():
    from backend.nodes.grain_visualization import GrainVisualization

    node = GrainVisualization()
    field, mask = _make_test_inputs()
    result, labeled = node.process(field, mask, style="inscribed_disc", fill=False)
    unique_ids = set(np.unique(labeled.data)) - {0.0}
    assert len(unique_ids) == 2, (
        f"Expected 2 unique nonzero grain labels, got {len(unique_ids)}: {unique_ids}"
    )


def test_disc_style():
    from backend.nodes.grain_visualization import GrainVisualization

    node = GrainVisualization()
    field, mask = _make_test_inputs()

    result_outline, _ = node.process(field, mask, style="inscribed_disc", fill=False)
    assert np.any(result_outline > 0), "inscribed_disc outline produced an empty mask"

    result_filled, _ = node.process(field, mask, style="inscribed_disc", fill=True)
    assert np.any(result_filled > 0), "inscribed_disc filled produced an empty mask"


def test_bounding_box_style():
    from backend.nodes.grain_visualization import GrainVisualization

    node = GrainVisualization()
    field, mask = _make_test_inputs()

    result_outline, _ = node.process(field, mask, style="bounding_box", fill=False)
    assert np.any(result_outline > 0), "bounding_box outline produced an empty mask"

    result_filled, _ = node.process(field, mask, style="bounding_box", fill=True)
    assert np.any(result_filled > 0), "bounding_box filled produced an empty mask"
