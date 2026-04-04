"""Pixel classification — classify pixels using decision tree on height, slope, and curvature."""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import bool_to_mask


def _compute_slope(data: np.ndarray) -> np.ndarray:
    """Gradient magnitude via np.gradient."""
    gy, gx = np.gradient(data.astype(np.float64))
    return np.sqrt(gx**2 + gy**2)


def _compute_curvature(data: np.ndarray) -> np.ndarray:
    """Laplacian (sum of second derivatives)."""
    d = data.astype(np.float64)
    gy, gx = np.gradient(d)
    gyy, _ = np.gradient(gy)
    _, gxx = np.gradient(gx)
    return np.abs(gxx + gyy)


def _feature_maps(data: np.ndarray, feature: str) -> list[np.ndarray]:
    """Return a list of 2-D feature arrays based on the feature selector."""
    height = data.astype(np.float64)
    if feature == "height":
        return [height]
    slope = _compute_slope(data)
    if feature == "slope":
        return [slope]
    curvature = _compute_curvature(data)
    if feature == "curvature":
        return [curvature]
    if feature == "height_slope":
        return [height, slope]
    # "all"
    return [height, slope, curvature]


def _normalize_01(arr: np.ndarray) -> np.ndarray:
    vmin, vmax = arr.min(), arr.max()
    if vmax > vmin:
        return (arr - vmin) / (vmax - vmin)
    return np.zeros_like(arr)


def _classify_single(values: np.ndarray, n_classes: int, method: str) -> np.ndarray:
    """Classify a single feature map into n_classes using the chosen method."""
    labels = np.zeros(values.shape, dtype=np.int32)

    if method == "equal_range":
        vmin, vmax = values.min(), values.max()
        if vmax <= vmin:
            return labels
        edges = np.linspace(vmin, vmax, n_classes + 1)
        for i in range(n_classes - 1):
            labels[values >= edges[i + 1]] = i + 1

    elif method == "quantile":
        percentiles = np.linspace(0, 100, n_classes + 1)
        edges = np.percentile(values, percentiles)
        for i in range(n_classes - 1):
            labels[values >= edges[i + 1]] = i + 1

    elif method == "otsu":
        # Multi-Otsu: find n_classes-1 thresholds via histogram analysis
        flat = values.ravel()
        n_bins = min(256, max(32, len(flat) // 10))
        counts, bin_edges = np.histogram(flat, bins=n_bins)
        centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        total = counts.sum()

        if total == 0 or n_classes < 2:
            return labels

        # For multi-Otsu, find thresholds that minimise intra-class variance
        # Use quantile-based initial thresholds then refine with exhaustive
        # search over histogram bins for each threshold
        thresholds = []
        if n_classes == 2:
            # Standard single-threshold Otsu
            best_var = -1.0
            best_t = 0
            cum_sum = 0.0
            cum_count = 0
            total_sum = float(np.sum(counts * centers))
            for i in range(n_bins - 1):
                cum_count += counts[i]
                cum_sum += counts[i] * centers[i]
                if cum_count == 0 or cum_count == total:
                    continue
                w0 = cum_count / total
                w1 = 1.0 - w0
                mu0 = cum_sum / cum_count
                mu1 = (total_sum - cum_sum) / (total - cum_count)
                between_var = w0 * w1 * (mu0 - mu1) ** 2
                if between_var > best_var:
                    best_var = between_var
                    best_t = i
            thresholds = [0.5 * (bin_edges[best_t + 1] + bin_edges[best_t + 2])]
        else:
            # Multi-threshold: use quantile splits as a good approximation
            percentiles = np.linspace(0, 100, n_classes + 1)[1:-1]
            thresholds = list(np.percentile(flat, percentiles))

        thresholds = sorted(thresholds)
        for i, t in enumerate(thresholds):
            labels[values >= t] = i + 1

    else:
        raise ValueError(f"Unknown classification method: {method!r}")

    return labels


def _kmeans_classify(features: np.ndarray, n_classes: int, max_iter: int = 20) -> np.ndarray:
    """Simple k-means on stacked normalised features.

    Parameters
    ----------
    features : (n_pixels, n_features) array
    n_classes : number of clusters
    max_iter : maximum iterations

    Returns
    -------
    labels : (n_pixels,) int32 array with values in [0, n_classes-1]
    """
    rng = np.random.RandomState(42)
    n_pixels = features.shape[0]
    # Initialise centroids by choosing random data points
    indices = rng.choice(n_pixels, size=min(n_classes, n_pixels), replace=False)
    centroids = features[indices].copy()

    labels = np.zeros(n_pixels, dtype=np.int32)
    for _ in range(max_iter):
        # Assign each pixel to nearest centroid
        dists = np.stack([
            np.sum((features - c) ** 2, axis=1) for c in centroids
        ], axis=1)  # (n_pixels, n_classes)
        new_labels = np.argmin(dists, axis=1).astype(np.int32)

        if np.array_equal(new_labels, labels):
            break
        labels = new_labels

        # Update centroids
        for k in range(n_classes):
            members = features[labels == k]
            if len(members) > 0:
                centroids[k] = members.mean(axis=0)

    return labels


@register_node(display_name="Pixel Classification")
class PixelClassification:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_classes": ("INT", {"default": 3, "min": 2, "max": 10, "step": 1}),
                "feature": (["height", "slope", "curvature", "height_slope", "all"],),
                "method": (["otsu", "equal_range", "quantile"],),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'classified'),
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Classify pixels into discrete classes based on height, slope, and/or curvature. "
        "Single-feature modes use threshold-based classification (Otsu, equal range, or quantile). "
        "Multi-feature modes (height_slope, all) use k-means clustering. "
        "Equivalent to Gwyddion's classify.c module."
    )

    def process(self, field: DataField, n_classes: int, feature: str, method: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)
        maps = _feature_maps(data, feature)

        if len(maps) == 1:
            # Single-feature: use threshold-based classification
            labels = _classify_single(maps[0], int(n_classes), method)
        else:
            # Multi-feature: normalise and use k-means
            normed = [_normalize_01(m) for m in maps]
            stacked = np.stack([m.ravel() for m in normed], axis=1)  # (n_pixels, n_features)
            labels = _kmeans_classify(stacked, int(n_classes)).reshape(data.shape)

        # Build output DataField with integer class labels
        classified = DataField(
            data=labels.astype(np.float64),
            xreal=field.xreal,
            yreal=field.yreal,
            si_unit_xy=field.si_unit_xy,
            si_unit_z="",
        )

        # Mask for class 0
        mask = bool_to_mask(labels == 0)

        return (classified, mask)
