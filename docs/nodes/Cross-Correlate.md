# Cross-Correlate

Compute 2D cross-correlation between two fields. The correlation peak indicates the offset where the two fields best match. Useful for drift measurement and feature alignment. Equivalent to Gwyddion crosscor.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First input field |
| field_b | DATA_FIELD | Yes | Second input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| correlation | DATA_FIELD | Cross-correlation map |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | same | Output size: full (Na+Nb−1), same (same as field_a), or valid (overlapping region only) |
| normalize | BOOLEAN | True | Normalize the result to [−1, 1] by dividing by the product of RMS values |

## Notes

- Both fields must be of compatible numpy array types; very different sizes in full mode produce large outputs.
- Mean is subtracted before correlation; absolute offset information is lost.
