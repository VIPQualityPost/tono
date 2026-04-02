# Curvature

Fit a quadratic surface and report the overall principal curvature radii and directions, matching Gwyddion's curvature feature. The output annotation marks the principal cross-sections and the node also returns the two corresponding height profiles.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topographic field |
| mask | IMAGE | No | Binary mask for including or excluding regions from the quadratic fit |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| output | ANNOTATION_SOURCE | Field with principal-axis lines overlaid |
| measurements | RECORD_TABLE | Curvature radii, principal-axis directions, center position and value |
| profile_a | LINE | Height profile along principal axis 1 |
| profile_b | LINE | Height profile along principal axis 2 |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| masking | dropdown | ignore | How to use the mask: ignore (fit all pixels), include (fit only masked pixels), or exclude (fit unmasked pixels) |

## Notes

- Requires at least six usable pixels for the quadratic fit; fewer pixels produce no output.
- The fit assumes a globally smooth quadratic surface; locally rough or step-like surfaces give unreliable results.
- Requires compatible XY and Z physical units (e.g. both in metres).
