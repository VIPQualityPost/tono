# Square Samples

Resample a DATA_FIELD so that its lateral pixel sizes dx and dy become equal (square samples), preserving the physical extents. Equivalent to the standard square-samples resampling operation.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to resample |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Resampled field with dx == dy and unchanged physical extents |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| interpolation | dropdown | cubic | Resampling interpolation: linear, cubic (B-spline-like), or nearest |

## Notes

- The algorithm works as follows: with sampling densities qx = xres/xreal and qy = yres/yreal, the axis sampled more coarsely gains pixels (`round(xreal*qy)` or `round(yreal*qx)`) so both axes end up with the same density; the other axis is unchanged.
- If |log(qx/qy)| is within 1/sqrt(xres^2 + yres^2) the densities are considered equal and the field is returned unchanged (duplicated).
- After resampling, dx = xreal/xres equals dy = yreal/yres, so each pixel is a physical square.
- Physical extents (xreal, yreal), offsets, and units are preserved.
