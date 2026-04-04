# Distribution Coercion

Transform pixel values so their distribution matches a target shape (uniform, Gaussian, or discrete levels) using rank-based reassignment. Equivalent to Gwyddion's coerce.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field whose value distribution will be transformed |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Field with pixel values reassigned to match the target distribution |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| distribution | dropdown | uniform | Target distribution shape: uniform, gaussian, or levels |
| n_levels | INT | 4 | Number of discrete output levels (2-1000); visible only for levels mode |
| processing | dropdown | field | Processing scope: field (entire array at once) or rows (line-by-line) |

## Notes

- The transformation is rank-based: pixels are sorted, then reassigned values drawn from the target distribution in sorted order. This preserves the relative ordering of all pixel values.
- Uniform mode spreads values evenly between the original minimum and maximum.
- Gaussian mode maps ranks to the inverse normal CDF, scaled to match the original mean and standard deviation.
- Levels mode quantizes the data into a fixed number of evenly spaced discrete values, useful for terrace-like visualization or discrete height analysis.
- Row mode applies the transformation independently to each scan line, which can correct line-to-line distribution variations in SPM data.
