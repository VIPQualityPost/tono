import numpy as np
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.pixel_classification import PixelClassification

    node = PixelClassification()
    field = make_field(shape=(64, 64))
    classified, mask = node.process(field, n_classes=3, feature="height", method="quantile")
    assert classified.data.shape == field.data.shape


def test_correct_number_of_classes():
    from backend.nodes.pixel_classification import PixelClassification

    node = PixelClassification()
    field = make_field(shape=(64, 64))
    for n in (2, 4, 5):
        classified, _ = node.process(field, n_classes=n, feature="height", method="quantile")
        unique = np.unique(classified.data)
        assert len(unique) <= n, f"Expected at most {n} classes, got {len(unique)}"


def test_equal_range_method():
    from backend.nodes.pixel_classification import PixelClassification

    node = PixelClassification()
    # Linear ramp: equal_range should produce evenly distributed labels
    ramp = np.linspace(0, 1, 64 * 64).reshape(64, 64)
    field = make_field(data=ramp)
    classified, _ = node.process(field, n_classes=4, feature="height", method="equal_range")
    labels = classified.data.astype(int)
    unique = np.unique(labels)
    assert len(unique) == 4
    # Each class should have roughly 25% of pixels
    counts = [np.sum(labels == u) for u in unique]
    for c in counts:
        assert abs(c - 64 * 64 / 4) < 64 * 64 * 0.05  # within 5%


def test_mask_output():
    from backend.nodes.pixel_classification import PixelClassification

    node = PixelClassification()
    field = make_field(shape=(32, 32))
    _, mask = node.process(field, n_classes=3, feature="height", method="otsu")
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)).issubset({0, 255})
