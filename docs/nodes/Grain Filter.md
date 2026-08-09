# Grain Filter

Remove grains from a binary mask based on size and border contact.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask | IMAGE | Yes | Binary mask containing grain regions to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered_mask | IMAGE | Binary mask with unwanted grains removed |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| min_area | INT | 10 | Discard grains with fewer pixels than this value (0 = no lower limit) |
| max_area | INT | 0 | Discard grains with more pixels than this value (0 = no upper limit) |
| remove_border | BOOLEAN | False | Discard any grain that touches the image edge |

## Notes

- Grain detection uses 4-connected or 8-connected labeling; the exact connectivity is determined by the implementation.
- min_area and max_area are in pixels, not physical units.
