import numpy as np
from tests.node_tests._shared import make_field


def test_output_shapes():
    from backend.nodes.neural_classification import NeuralClassification

    node = NeuralClassification()
    data = np.random.default_rng(0).standard_normal((32, 32))
    field = make_field(data=data)

    mask, prob_field = node.process(field, n_gaussians=3, n_hidden=8,
                                    train_steps=20, seed=7)
    assert mask.shape == (32, 32)
    assert prob_field.data.shape == (32, 32)


def test_mask_is_binary():
    from backend.nodes.neural_classification import NeuralClassification

    node = NeuralClassification()
    data = np.random.default_rng(1).standard_normal((24, 24))
    field = make_field(data=data)

    mask, _ = node.process(field, n_gaussians=2, n_hidden=8,
                           train_steps=10, seed=0)
    unique = set(np.unique(mask).tolist())
    assert unique <= {0, 255}, f"Unexpected mask values: {unique}"


def test_probability_range():
    from backend.nodes.neural_classification import NeuralClassification

    node = NeuralClassification()
    data = np.random.default_rng(2).standard_normal((32, 32))
    field = make_field(data=data)

    _, prob_field = node.process(field, n_gaussians=4, n_hidden=16,
                                train_steps=50, seed=42)
    assert prob_field.data.min() >= 0.0
    assert prob_field.data.max() <= 1.0


def test_with_training_mask():
    from backend.nodes.neural_classification import NeuralClassification

    node = NeuralClassification()

    # Create a field with two distinct height regions
    data = np.zeros((48, 48), dtype=np.float64)
    data[:, 24:] = 5.0  # right half is elevated
    field = make_field(data=data)

    # Training mask: left half = 0 (class A), right half = 255 (class B)
    training_mask = np.zeros((48, 48), dtype=np.uint8)
    training_mask[:, 24:] = 255

    mask, prob_field = node.process(field, n_gaussians=4, n_hidden=16,
                                    train_steps=200, seed=42,
                                    training_mask=training_mask)

    assert mask.dtype == np.uint8
    assert mask.shape == (48, 48)
    assert prob_field.data.shape == (48, 48)

    # The network should learn to classify the two regions correctly.
    # Check that most of the right half is class B and left half is class A.
    right_classified = np.count_nonzero(mask[:, 24:] == 255)
    left_classified = np.count_nonzero(mask[:, :24] == 0)
    total_half = 48 * 24
    assert right_classified > total_half * 0.8, "Right half should mostly be class B"
    assert left_classified > total_half * 0.8, "Left half should mostly be class A"
