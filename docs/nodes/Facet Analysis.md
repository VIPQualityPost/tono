# Facet Analysis

Compute the facet orientation distribution of a surface. Outputs a 2D histogram (stereographic projection) where the x-axis is the azimuthal angle and y-axis is the inclination. Equivalent to Gwyddion's facet_analysis.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| facet_map | DATA_FIELD | 2D histogram of facet orientations (phi vs theta) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_bins | INT | 180 | Number of azimuthal bins; theta bins = n_bins/4 (30–720) |
| kernel_size | INT | 3 | Sobel gradient kernel size in pixels (3–9, odd) |

## Notes

- The output is a normalised probability density — it sums to 1.0.
- X-axis: azimuthal angle phi (0–360°). Y-axis: inclination theta (0° = flat, max = steepest facet).
- A flat surface produces a single bright spot near theta=0. A surface with distinct facets shows multiple peaks.
- Larger kernel_size smooths the gradient estimate, reducing noise sensitivity.
