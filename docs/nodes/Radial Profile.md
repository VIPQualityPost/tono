# Radial Profile

Compute the azimuthally averaged radial profile from a centre point. The output x-axis is radius in physical xy units. Equivalent to gwy_data_field_angular_average used by Gwyddion's Radial Profile tool.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| profile | LINE | Radially averaged profile vs. radius |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| cx | FLOAT | 0.5 | Centre x position as a fraction of field width (0 = left, 1 = right) |
| cy | FLOAT | 0.5 | Centre y position as a fraction of field height (0 = top, 1 = bottom) |
| n_bins | INT | 128 | Number of radial bins (4–4096) |

## Notes

- Pixels are assigned to radial bins by Euclidean distance; bins near the centre contain fewer pixels and may be noisier.
- Physical x-axis units come from the field's si_unit_xy; uncalibrated fields produce pixel-unit radii.
