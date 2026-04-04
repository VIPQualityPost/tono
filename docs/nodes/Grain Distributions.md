# Grain Distributions

Compute a histogram distribution of a grain property from a labeled mask. Supported properties: area, equivalent diameter, mean height, max height, volume, and boundary length. Equivalent to Gwyddion's grain_dist.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface data |
| mask | IMAGE | Yes | Binary mask defining grain regions |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| distribution | LINE_DATA | Histogram of the selected grain property |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| property | dropdown | area | Grain property to plot: area, equiv_diameter, mean_height, max_height, volume, boundary_length |
| n_bins | INT | 30 | Number of histogram bins (5–200) |
| min_size | INT | 10 | Minimum grain size in pixels to include (1–100000) |

## Notes

- Volume is computed relative to the mean height of the non-grain (background) region.
- Boundary length is estimated by counting boundary pixels and multiplying by the pixel size.
- For per-grain statistics (not histograms), use Grain Analysis instead.
- For aggregate summary statistics, use Grain Summary.
