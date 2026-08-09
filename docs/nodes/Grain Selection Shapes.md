# Grain Selection Shapes

Create a selection image visualizing the largest disc that fits inside each grain (inscribed discs) or the smallest circle enclosing each grain (circumscribed circles). This mirrors the standard Select Inscribed Discs and Select Circumscribed Circles operations.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask | IMAGE | Yes | Binary grain mask (0/255); grains are 4-connected components |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| selection | IMAGE | Binary mask with the inscribed discs or circumscribed circles filled in white (uint8, 0/255) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | inscribed_discs | inscribed_discs: largest disc that fits inside each grain; circumscribed_circles: smallest circle enclosing each grain |
| min_area | INT | 0 | Minimum grain area in pixels; smaller grains are skipped |

## Notes

- Inscribed discs are found with the Euclidean distance transform: the disc center is the pixel of maximal distance from the grain boundary (ties resolved towards the grain center of mass) and the radius is the distance converted to a continuous half-width. This matches the inscribed-disc quantity up to the half-pixel discretization that the upsampled algorithm resolves.
- Circumscribed circles are computed over the convex hull of each grain's pixel corners, using a centroid start plus a greedy 12-direction refinement, so the circle is the smallest enclosing circle of the grain corners.
- Circles are rasterized as filled discs in pixel space; no field is required, so non-square pixels are treated as isotropic.
