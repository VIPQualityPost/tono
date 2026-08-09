"""Neural network classification — classify pixels using a simple feedforward network."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


def _extract_features(data: np.ndarray, n_gaussians: int) -> np.ndarray:
    """Build multi-scale Gaussian feature matrix from 2-D data.

    For each scale sigma = 2^i (i = 0 .. n_gaussians-1), compute
    gaussian_filter(data, sigma) and stack as feature columns.
    Each feature is normalised to zero mean and unit variance.
    """
    rows, cols = data.shape
    features = np.empty((rows * cols, n_gaussians), dtype=np.float64)

    for i in range(n_gaussians):
        sigma = 2.0 ** i
        blurred = gaussian_filter(data, sigma).ravel()
        mean = blurred.mean()
        std = blurred.std()
        if std > 0:
            blurred = (blurred - mean) / std
        else:
            blurred = blurred - mean
        features[:, i] = blurred

    return features


def _forward(X: np.ndarray, W1: np.ndarray, b1: np.ndarray,
             W2: np.ndarray, b2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward pass through a 2-layer sigmoid network."""
    h = _sigmoid(X @ W1 + b1)
    y = _sigmoid(h @ W2 + b2)
    return h, y


def _train_network(
    X: np.ndarray,
    targets: np.ndarray,
    W1: np.ndarray,
    b1: np.ndarray,
    W2: np.ndarray,
    b2: np.ndarray,
    train_steps: int,
    lr: float = 0.1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Train via gradient descent with binary cross-entropy loss."""
    eps = 1e-7
    n = X.shape[0]
    t = targets.reshape(-1, 1)

    for _ in range(train_steps):
        # Forward
        h, y = _forward(X, W1, b1, W2, b2)

        # Clamp to avoid log(0)
        y_clamped = np.clip(y, eps, 1.0 - eps)

        # Backward — output layer
        dy = (y_clamped - t) / (y_clamped * (1.0 - y_clamped) + eps)
        dy *= y * (1.0 - y)  # sigmoid derivative

        dW2 = (h.T @ dy) / n
        db2 = dy.mean(axis=0)

        # Backward — hidden layer
        dh = (dy @ W2.T) * h * (1.0 - h)
        dW1 = (X.T @ dh) / n
        db1 = dh.mean(axis=0)

        # Update
        W1 -= lr * dW1
        b1 -= lr * db1
        W2 -= lr * dW2
        b2 -= lr * db2

    return W1, b1, W2, b2


@register_node(display_name="Neural Classification")
class NeuralClassification:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_gaussians": ("INT", {"default": 4, "min": 1, "max": 10, "step": 1}),
                "n_hidden": ("INT", {"default": 16, "min": 4, "max": 128, "step": 1}),
                "train_steps": ("INT", {"default": 200, "min": 10, "max": 5000, "step": 1}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999, "step": 1}),
            },
            "optional": {
                "training_mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
        ('DATA_FIELD', 'probability'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Classify surface pixels into two classes using a simple two-layer "
        "feedforward neural network with sigmoid activations. Features are "
        "extracted via multi-scale Gaussian filtering. When a training mask "
        "is provided the network learns from labelled pixels; otherwise it "
        "uses unsupervised self-labelling from the initial random projection."
    )

    KEYWORDS = ("machine learning", "ml", "segment", "nn", "feedforward", "classifier")

    def process(
        self,
        field: DataField,
        n_gaussians: int,
        n_hidden: int,
        train_steps: int,
        seed: int,
        training_mask: np.ndarray | None = None,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        yres, xres = data.shape
        n_features = int(n_gaussians)
        n_hidden = int(n_hidden)
        train_steps = int(train_steps)

        # 1. Feature extraction
        X_all = _extract_features(data, n_features)

        # 2. Initialise weights
        rng = np.random.default_rng(int(seed))
        scale1 = np.sqrt(2.0 / n_features)
        W1 = rng.standard_normal((n_features, n_hidden)) * scale1
        b1 = np.zeros(n_hidden)
        scale2 = np.sqrt(2.0 / n_hidden)
        W2 = rng.standard_normal((n_hidden, 1)) * scale2
        b2 = np.zeros(1)

        # 3/4. Training
        if training_mask is not None:
            # Supervised — use labelled pixels
            mask_bool = mask_to_bool(training_mask)
            if mask_bool.shape != data.shape:
                raise ValueError(
                    f"Training mask shape {mask_bool.shape} does not match "
                    f"field shape {data.shape}."
                )
            # Class B = masked (255), class A = unmasked but we need both labels.
            # Pixels that are 0 are class A, pixels that are 255 are class B.
            # We train on ALL pixels that have a definitive label.
            labels_flat = training_mask.ravel().astype(np.float64) / 255.0
            # Use all pixels as training data (0 = class A, 1 = class B)
            X_train = X_all
            targets = labels_flat
            W1, b1, W2, b2 = _train_network(
                X_train, targets, W1, b1, W2, b2, train_steps,
            )
        else:
            # Unsupervised — use random projection to create initial labels,
            # then refine with self-training.
            _, y_init = _forward(X_all, W1, b1, W2, b2)
            self_labels = (y_init.ravel() > 0.5).astype(np.float64)
            # Train on the self-assigned labels for a few iterations
            steps = min(train_steps, 50)
            W1, b1, W2, b2 = _train_network(
                X_all, self_labels, W1, b1, W2, b2, steps,
            )

        # 5. Apply trained network to all pixels
        _, prob_flat = _forward(X_all, W1, b1, W2, b2)
        probability = prob_flat.reshape(yres, xres)

        # 6. Build outputs
        mask = bool_to_mask(probability > 0.5)

        prob_field = DataField(
            data=probability,
            xreal=field.xreal,
            yreal=field.yreal,
            xoff=field.xoff,
            yoff=field.yoff,
            si_unit_xy=field.si_unit_xy,
            si_unit_z="",
            domain="spatial",
        )

        return (mask, prob_field)
