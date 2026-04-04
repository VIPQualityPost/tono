# Grain Edge

Detect grain boundaries from a binary grain mask. Outputs a mask of pixels at grain/non-grain borders using 4-neighbour connectivity. Width controls the boundary thickness in pixels. Equivalent to Gwyddion's grain_edge.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field (used for dimension reference) |
| mask | IMAGE | Yes | Binary grain mask (white = grain) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| edge_mask | IMAGE | Binary mask with grain boundary pixels marked |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| width | INT | 1 | Boundary thickness in pixels; values greater than 1 dilate the edge outward (1–10) |

## Notes

- A grain pixel is on the boundary if at least one of its 4-connected neighbours (up, down, left, right) is not a grain pixel.
- When width > 1, the boundary is expanded using binary dilation with a square structuring element of size (2*width - 1).
- Dilation is masked to stay within the original grain region, so boundaries never extend into non-grain areas.
- The field and mask must have the same pixel dimensions.
