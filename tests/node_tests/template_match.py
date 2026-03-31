import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_template_match_exact_match_score_one():
    """When template equals the image, the peak score should be 1."""
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(0)
    data = rng.standard_normal((32, 32))
    image_field = make_field(data=data)
    # Template is the full image → perfect correlation everywhere → peak = 1
    template_field = make_field(data=data)
    node = TemplateMatch()
    score_field, detections = node.process(image_field, template_field, threshold=0.9)
    assert score_field.data.max() == pytest.approx(1.0, abs=1e-6)


def test_template_match_output_shape_matches_image():
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(1)
    image_field = make_field(data=rng.standard_normal((32, 32)))
    template_field = make_field(data=rng.standard_normal((8, 8)))
    node = TemplateMatch()
    score_field, detections = node.process(image_field, template_field, threshold=0.5)
    assert score_field.data.shape == image_field.data.shape
    assert detections.shape == image_field.data.shape


def test_template_match_score_in_range():
    """Score values should be clipped to [0, 1]."""
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(2)
    image_field = make_field(data=rng.standard_normal((32, 32)))
    template_field = make_field(data=rng.standard_normal((6, 6)))
    node = TemplateMatch()
    score_field, _ = node.process(image_field, template_field, threshold=0.5)
    assert score_field.data.min() >= 0.0 - 1e-10
    assert score_field.data.max() <= 1.0 + 1e-10


def test_template_match_detections_binary():
    """Detection mask values should be 0 or 255 only."""
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(3)
    image_field = make_field(data=rng.standard_normal((32, 32)))
    template_field = make_field(data=rng.standard_normal((8, 8)))
    node = TemplateMatch()
    _, detections = node.process(image_field, template_field, threshold=0.5)
    unique_values = set(np.unique(detections))
    assert unique_values <= {0, 255}


def test_template_match_threshold_zero_all_detected():
    """threshold=0 should mark all pixels as detections (score always >= 0)."""
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(4)
    image_field = make_field(data=rng.standard_normal((16, 16)))
    template_field = make_field(data=rng.standard_normal((4, 4)))
    node = TemplateMatch()
    _, detections = node.process(image_field, template_field, threshold=0.0)
    assert np.all(detections == 255)


def test_template_match_threshold_one_sparse_detections():
    """threshold=1.0 should detect very few (or no) positions."""
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(5)
    image_field = make_field(data=rng.standard_normal((32, 32)))
    template_field = make_field(data=rng.standard_normal((8, 8)))
    node = TemplateMatch()
    _, detections = node.process(image_field, template_field, threshold=1.0)
    # At threshold=1.0, only perfect matches count (rare for random data)
    detected_count = int((detections == 255).sum())
    assert detected_count < 10  # very few or none


def test_template_match_preserves_metadata():
    from backend.nodes.template_match import TemplateMatch

    rng = np.random.default_rng(6)
    image_field = make_field(data=rng.standard_normal((32, 32)))
    template_field = make_field(data=rng.standard_normal((8, 8)))
    node = TemplateMatch()
    score_field, _ = node.process(image_field, template_field, threshold=0.5)
    assert score_field.xreal == image_field.xreal
    assert score_field.yreal == image_field.yreal
