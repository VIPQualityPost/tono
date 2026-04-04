# Neural Classification

Classify surface pixels into two classes using a simple two-layer feedforward neural network with sigmoid activations. Features are extracted via multi-scale Gaussian filtering. Equivalent in purpose to Gwyddion's neural.c classifier.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface to classify |
| training_mask | IMAGE | No | Training labels: 0 = class A, 255 = class B. When omitted the network uses unsupervised self-labelling |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary classification mask (0 or 255) |
| probability | DATA_FIELD | Per-pixel probability of belonging to class B (values in 0-1) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_gaussians | INT | 4 | Number of Gaussian blur scales for feature extraction (1-10). Each scale uses sigma = 2^i |
| n_hidden | INT | 16 | Number of neurons in the hidden layer (4-128) |
| train_steps | INT | 200 | Number of gradient descent iterations (10-5000) |
| seed | INT | 42 | Random seed for weight initialisation (0-999999) |

## Notes

- Feature extraction applies Gaussian blur at multiple scales (sigma = 1, 2, 4, 8, ...) to capture both fine and coarse surface structure. Each feature is normalised to zero mean and unit variance before training.
- The network architecture is input -> hidden (sigmoid) -> output (sigmoid), trained with binary cross-entropy loss and standard backpropagation.
- When a training mask is provided, the network learns in supervised mode using all pixels (0 pixels as class A targets, 255 pixels as class B targets).
- Without a training mask, the node uses an unsupervised approach: the random initial weights produce an initial classification which is then refined by self-training for a small number of steps.
- Increasing n_hidden or train_steps improves capacity but slows computation. For most surfaces, the defaults work well.
- The probability output can be fed into a Threshold Mask node for adjustable post-classification thresholding.
