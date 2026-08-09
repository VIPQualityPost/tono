# Square Samples

Resample a DATA_FIELD so that its lateral pixel sizes dx and dy become equal (square samples), preserving the physical extents. Equivalent to Gwyddion's `square_samples` basic operation (module `basicops.c`), which resamples via `gwy_data_field_new_resampled`.

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
| interpolation | dropdown | cubic | Resampling interpolation: linear, cubic (B-spline-like, closest to Gwyddion's B-spline), or nearest |

## Notes

- The algorithm mirrors Gwyddion: with sampling densities qx = xres/xreal and qy = yres/yreal, the axis sampled more coarsely gains pixels (`round(xreal*qy)` or `round(yreal*qx)`) so both axes end up with the same density; the other axis is unchanged.
- If |log(qx/qy)| is within 1/sqrt(xres^2 + yres^2) the densities are considered equal and the field is returned unchanged (duplicated), exactly like Gwyddion.
- After resampling, dx = xreal/xres equals dy = yreal/yres, so each pixel is a physical square.
- Physical extents (xreal, yreal), offsets, and units are preserved.
