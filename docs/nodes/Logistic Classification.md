# Logistic Classification

Classify surface features using logistic regression on engineered height-derived features. Optionally accepts a training mask; otherwise an Otsu-based threshold generates pseudo-labels automatically.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topographic surface to classify |
| training_mask | IMAGE | No | Optional training labels — masked pixels are treated as the positive class |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary classification result (0 or 255) |
| probability | DATA_FIELD | Per-pixel probability from the logistic model (values in [0, 1]) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| use_gaussians | BOOLEAN | True | Include Gaussian blur features at multiple scales |
| n_gaussians | INT | 4 | Number of Gaussian scales (1-10). Only shown when use_gaussians is True |
| use_sobel | BOOLEAN | True | Include Sobel gradient features (horizontal and vertical) |
| use_laplacian | BOOLEAN | True | Include Laplacian (sum of second differences) feature |
| regularization | FLOAT | 1.0 | L2 regularization strength lambda (0.0-10.0) |
| max_iter | INT | 500 | Maximum gradient descent iterations (10-5000) |
| seed | INT | 42 | Random seed for reproducibility (0-999999) |

## Notes

- **Feature engineering:** The classifier always uses normalized raw height as a feature. Gaussian blurs at scales 2^0, 2^1, ..., 2^(n-1) capture multi-scale smoothness. Sobel gradients detect edges, and the Laplacian highlights curvature. All features are standardized to zero mean and unit variance before training.
- **L2 regularization:** The regularization parameter controls overfitting by penalizing large weights. Higher values produce smoother, more generalizable decision boundaries. The bias term is not regularized.
- **Logistic regression vs neural networks:** Logistic regression is a linear classifier — it learns a single hyperplane in feature space. For complex, highly non-linear boundaries a neural network may be more appropriate, but logistic regression is fast, interpretable, and often sufficient when combined with good feature engineering.
- **Unsupervised mode:** When no training mask is provided, the node uses an Otsu-like threshold on the raw height to generate pseudo-labels, then trains the classifier on those labels. This can improve on simple thresholding because the classifier leverages multi-scale and gradient features.
- Equivalent to Gwyddion's logistic.c classification functionality.
