# MFM Lift Estimate

Estimates the lift height difference between two MFM images of the same area measured at different heights, from the frequency-dependent blur of the data. Equivalent to Gwyddion's mfm_findshift module (gwy_data_field_mfm_find_shift_z).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Reference MFM image (typically the sharper one, measured at smaller lift) |
| shifted | DATA_FIELD | Yes | Second MFM image of the same area, same resolution |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| estimated | DATA_FIELD | Residual: the reference image propagated by the estimated shift minus the second image |
| measurement | RECORD_TABLE | Estimated lift shift and search range (in m) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| start | FLOAT | 10e-9 | Lower bound of the shift search range in metres |
| stop | FLOAT | 20e-9 | Upper bound of the shift search range in metres |

## Notes

- The estimate minimises ||shift_z(field, z) − shifted||² over z in [start, stop] using Gwyddion's 1-D minimiser (12-point scan plus parabolic/bisection refinement), with the transfer function exp(−2π|k|z).
- Sign convention (same as gwy_data_field_mfm_shift_z): a positive estimate means the second image was measured at a larger lift height (blurrier) than the reference; negative means smaller. The estimate is generally only meaningful when the second image was measured at the larger lift height.
- The search range is ordered internally: start > stop is allowed.
- Both images must have the same resolution; the lateral calibration of the reference image is used for the frequency grid.
