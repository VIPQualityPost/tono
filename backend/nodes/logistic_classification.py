"""Logistic classification — classify features using logistic regression."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask


def _build_features(data: np.ndarray, use_gaussians: bool, n_gaussians: int,
                    use_sobel: bool, use_laplacian: bool) -> np.ndarray:
    """Build a feature matrix from the height field.

    Each feature is normalized to zero mean, unit variance.  The raw
    (normalized) height is always included as the first feature.
    """
    h, w = data.shape
    features: list[np.ndarray] = []

    # Always include raw height (normalized)
    features.append(data.ravel().copy())

    # Gaussian blur features at increasing scales
    if use_gaussians:
        for i in range(int(n_gaussians)):
            sigma = float(2 ** i)
            features.append(gaussian_filter(data, sigma).ravel())

    # Sobel gradient features
    if use_sobel:
        features.append(sobel(data, axis=0).ravel())
        features.append(sobel(data, axis=1).ravel())

    # Laplacian feature (sum of second differences)
    if use_laplacian:
        lap = np.zeros_like(data)
        lap[1:-1, :] += data[:-2, :] - 2 * data[1:-1, :] + data[2:, :]
        lap[:, 1:-1] += data[:, :-2] - 2 * data[:, 1:-1] + data[:, 2:]
        features.append(lap.ravel())

    # Stack into (n_pixels, n_features) matrix
    X = np.column_stack(features)

    # Normalize each feature to zero mean, unit variance
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    X = (X - means) / stds

    # Add bias column
    X = np.column_stack([np.ones(X.shape[0]), X])

    return X


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def _otsu_threshold(data: np.ndarray) -> float:
    """Simple Otsu threshold on flattened data."""
    flat = data.ravel()
    counts, bin_edges = np.histogram(flat, bins=256)
    centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    total = counts.sum()
    if total == 0:
        return float(np.median(flat))

    sum_total = (counts * centers).sum()
    sum_bg = 0.0
    weight_bg = 0.0
    best_var = -1.0
    best_thresh = float(centers[0])

    for i in range(len(counts)):
        weight_bg += counts[i]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += counts[i] * centers[i]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var_between > best_var:
            best_var = var_between
            best_thresh = float(centers[i])

    return best_thresh


def _train_logistic(X: np.ndarray, y: np.ndarray, regularization: float,
                    max_iter: int, seed: int) -> np.ndarray:
    """Train logistic regression via gradient descent.

    Parameters
    ----------
    X : (m, n_features+1) array with bias column already included.
    y : (m,) binary labels (0 or 1).
    regularization : L2 penalty lambda.
    max_iter : maximum gradient descent iterations.
    seed : random seed (unused here; theta starts at zeros).

    Returns
    -------
    theta : (n_features+1,) weight vector.
    """
    rng = np.random.default_rng(seed)
    n = X.shape[1]
    theta = np.zeros(n)
    m = len(y)
    lr = 0.1

    for _ in range(max_iter):
        h = _sigmoid(X @ theta)
        error = h - y

        grad = X.T @ error / m
        # L2 regularization (don't regularize bias at index 0)
        reg_term = (regularization / m) * theta
        reg_term[0] = 0.0
        grad += reg_term

        theta -= lr * grad

        if np.linalg.norm(grad) < 1e-6:
            break

    return theta


@register_node(display_name="Logistic Classification")
class LogisticClassification:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "use_gaussians": ("BOOLEAN", {"default": True}),
                "n_gaussians": ("INT", {
                    "default": 4, "min": 1, "max": 10,
                    "show_when_widget_value": {"use_gaussians": [True]},
                }),
                "use_sobel": ("BOOLEAN", {"default": True}),
                "use_laplacian": ("BOOLEAN", {"default": True}),
                "regularization": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
                "max_iter": ("INT", {"default": 500, "min": 10, "max": 5000}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999}),
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
        "Classify surface features using logistic regression on engineered "
        "height-derived features (Gaussian blurs, Sobel gradients, Laplacian). "
        "Optionally accepts a training mask; otherwise an Otsu-based threshold "
        "generates pseudo-labels automatically."
    )

    def process(
        self,
        field: DataField,
        use_gaussians: bool,
        n_gaussians: int,
        use_sobel: bool,
        use_laplacian: bool,
        regularization: float,
        max_iter: int,
        seed: int,
        training_mask: np.ndarray | None = None,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        h, w = data.shape

        # Build feature matrix for all pixels
        X_all = _build_features(data, use_gaussians, n_gaussians, use_sobel, use_laplacian)

        if training_mask is not None:
            # Extract training labels from the mask
            mask_bool = mask_to_bool(training_mask)
            if mask_bool.shape[:2] != (h, w):
                raise ValueError(
                    f"Training mask shape {mask_bool.shape} does not match "
                    f"field shape {(h, w)}."
                )
            labeled_pixels = mask_bool.ravel()
            # Use masked pixels as positive class, unmasked as negative
            y_train = labeled_pixels.astype(np.float64)
            X_train = X_all
        else:
            # No training mask: use Otsu threshold to create pseudo-labels
            threshold = _otsu_threshold(data)
            y_train = (data.ravel() >= threshold).astype(np.float64)
            X_train = X_all

        # Train logistic regression
        theta = _train_logistic(X_train, y_train, regularization, max_iter, seed)

        # Apply to all pixels
        probability = _sigmoid(X_all @ theta).reshape(h, w)

        # Create binary mask
        mask = bool_to_mask(probability > 0.5)

        # Emit preview
        from backend.execution_context import emit_preview
        from backend.data_types import encode_preview
        from backend.nodes.helpers import _mask_overlay
        emit_preview(encode_preview(_mask_overlay(field, mask)))

        # Build probability output as a DataField
        prob_field = field.replace(data=probability, si_unit_z="")

        return (mask, prob_field)
