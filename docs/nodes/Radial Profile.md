# Radial Profile

Compute an **azimuthally averaged** profile around a centre point on a DATA_FIELD. At each radius, every pixel in the full 360° ring around the centre is averaged together, so the profile is direction-independent — there is no clockwise/counter-clockwise traversal and no start or end point along the ring. The output is a single 1-D profile: value vs. radius.

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
| n_bins | INT | 128 | Number of radial bins (4-4096) |

## Interactive preview

The dashed circle around the centre shows the outer radius used by the profile. Pixels beyond it are not included in the averaging.

## Notes

- Pixels are assigned to radial bins by Euclidean distance from the centre; inner bins contain fewer pixels and may be noisier.
- Physical x-axis units come from the field's si_unit_xy; uncalibrated fields produce pixel-unit radii.
