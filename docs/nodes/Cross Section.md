# Cross Section

Extract a cross-section height profile along a line between two draggable points on a DATA_FIELD. Equivalent to gwy_data_field_get_profile.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |
| marker_pair | COORDPAIR | No | Locks both line endpoints from an external coordinate pair |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| profile | LINE | Height profile along the cross-section line |
| marker_pair | COORDPAIR | Current endpoint coordinates (passthrough for chaining) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| extend | dropdown | none | none: profile between the two markers; to_edges: extend line to image borders |
| n_samples | INT | 0 | Number of sample points along the profile (0 = auto, one per pixel diagonal) |

## Limitations

- Profile is sampled using cubic spline interpolation (order 3); sharp step edges may show ringing.
- Physical x-axis of the output profile is the Euclidean distance in field xy units.
