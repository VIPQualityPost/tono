# Entropy

Compute the Shannon entropy of the height or slope distribution. H = -Σ p·ln(p). Equivalent to Gwyddion entropy.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| entropy | FLOAT | Shannon entropy in nats |
| normalised_entropy | FLOAT | Entropy divided by ln(n_bins), in [0, 1] |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | height values | Compute entropy of height values or slope magnitude |
| n_bins | INT | 256 | Number of histogram bins for probability estimation (16-1024) |

## Notes

- Entropy is sensitive to n_bins; very few bins underestimate entropy while very many bins overestimate it for small fields.
- Non-finite pixel values are removed before binning.
