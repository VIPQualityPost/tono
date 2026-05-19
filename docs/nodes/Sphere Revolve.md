# Sphere Revolve

Subtract a spherical cap background. A sphere of the given radius is rolled under the surface, and the envelope it traces is subtracted as the background.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with spherical background subtracted |
| background | DATA_FIELD | The estimated spherical background |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| radius | INT | 20 | Sphere radius in pixels (1–500) |

## Notes

- Works like Arc Revolve but in two dimensions — suitable for bowl-shaped or dome-shaped backgrounds.
- Larger radii produce smoother backgrounds. Very small radii will track individual features.
- Deep outliers are suppressed before fitting.
