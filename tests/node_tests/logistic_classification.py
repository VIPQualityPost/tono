import numpy as np
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_output_shapes():
    from backend.nodes.logistic_classification import LogisticClassification
    node = LogisticClassification()

    data = np.random.default_rng(0).standard_normal((64, 64))
    field = make_field(data=data)

    previews = []
    with execution_callbacks(preview=lambda nid, uri: previews.append(uri)), active_node("test"):
        mask, prob, model_stats = node.process(
            field,
            use_gaussians=True,
            n_gaussians=4,
            use_sobel=True,
            use_laplacian=True,
            regularization=1.0,
            max_iter=500,
            seed=42,
        )

    assert mask.shape == field.data.shape
    assert prob.data.shape == field.data.shape
    # Model stats is a standard {quantity, value, unit} record table.
    assert len(model_stats) >= 3
    assert all(set(row) == {"quantity", "value", "unit"} for row in model_stats)


def test_mask_binary():
    from backend.nodes.logistic_classification import LogisticClassification
    node = LogisticClassification()

    data = np.zeros((32, 32))
    data[:, 16:] = 1.0
    field = make_field(data=data)

    with execution_callbacks(preview=lambda nid, uri: None), active_node("test"):
        mask, _, _ = node.process(
            field,
            use_gaussians=True,
            n_gaussians=2,
            use_sobel=True,
            use_laplacian=True,
            regularization=1.0,
            max_iter=500,
            seed=42,
        )

    unique = set(np.unique(mask))
    assert unique <= {0, 255}, f"Mask contains non-binary values: {unique}"


def test_probability_range():
    from backend.nodes.logistic_classification import LogisticClassification
    node = LogisticClassification()

    data = np.random.default_rng(7).standard_normal((48, 48))
    field = make_field(data=data)

    with execution_callbacks(preview=lambda nid, uri: None), active_node("test"):
        _, prob, _ = node.process(
            field,
            use_gaussians=True,
            n_gaussians=3,
            use_sobel=True,
            use_laplacian=True,
            regularization=1.0,
            max_iter=500,
            seed=42,
        )

    assert prob.data.min() >= 0.0, f"Probability min {prob.data.min()} < 0"
    assert prob.data.max() <= 1.0, f"Probability max {prob.data.max()} > 1"


def test_with_training():
    from backend.nodes.logistic_classification import LogisticClassification
    node = LogisticClassification()

    # Create a field with two distinct regions
    data = np.zeros((64, 64))
    data[:, 32:] = 2.0
    data += np.random.default_rng(1).standard_normal((64, 64)) * 0.1
    field = make_field(data=data)

    # Create a training mask marking the right half as positive
    training_mask = np.zeros((64, 64), dtype=np.uint8)
    training_mask[:, 32:] = 255

    with execution_callbacks(preview=lambda nid, uri: None), active_node("test"):
        mask, prob, model_stats = node.process(
            field,
            use_gaussians=True,
            n_gaussians=3,
            use_sobel=True,
            use_laplacian=True,
            regularization=1.0,
            max_iter=500,
            seed=42,
            training_mask=training_mask,
        )

    assert mask.dtype == np.uint8
    assert mask.shape == field.data.shape
    # The classifier should learn that the right half is positive
    right_positive = np.count_nonzero(mask[:, 32:] == 255)
    left_positive = np.count_nonzero(mask[:, :32] == 255)
    assert right_positive > left_positive, (
        f"Expected more positives on right ({right_positive}) than left ({left_positive})"
    )
    # Training was performed on the full field: accuracy, pixel count and weights are reported.
    assert all(set(row) == {"quantity", "value", "unit"} for row in model_stats)
    quantities = {row["quantity"] for row in model_stats}
    assert "Training accuracy" in quantities
    assert "Training pixels" in quantities
    training_pixels = next(row["value"] for row in model_stats
                           if row["quantity"] == "Training pixels")
    assert training_pixels == 64 * 64
    accuracy = next(row["value"] for row in model_stats
                    if row["quantity"] == "Training accuracy")
    assert 0.0 <= accuracy <= 1.0
