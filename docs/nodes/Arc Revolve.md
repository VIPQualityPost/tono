# Arc Revolve

Subtract a cylindrical arc background. A circular arc of the given radius is rolled under each row (or column), and the envelope it traces is subtracted as the background.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with arc background subtracted |
| background | DATA_FIELD | The estimated arc background |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| radius | INT | 20 | Arc radius in pixels (1–1000) |
| direction | dropdown | horizontal | Direction to apply the arc: horizontal, vertical, or both |

## Notes

- Larger radii produce smoother backgrounds that follow gentle curvature. Smaller radii track finer features.
- The "both" direction takes the minimum of horizontal and vertical backgrounds.
- Deep outliers are suppressed before fitting so that scratches or pits do not pull the arc down.
