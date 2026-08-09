# Tilt

Apply or remove a linear tilt (planar slope) from a DATA_FIELD. The tilt is defined by slope values in data units per physical unit along the x and y directions.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| tilted | DATA_FIELD | Field with tilt applied or removed |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| slope_x | FLOAT | 0.0 | Slope along the x axis in data units per physical unit (e.g. nm/um) |
| slope_y | FLOAT | 0.0 | Slope along the y axis in data units per physical unit (e.g. nm/um) |
| mode | dropdown | subtract | Operation mode: subtract (remove tilt) or add (apply tilt) |

## Notes

- In subtract mode the specified planar slope is removed from the field, useful for compensating known sample tilt.
- In add mode the slope is added, useful for simulating a tilted surface or restoring a previously subtracted tilt.
- The slope values are in data-unit per physical-unit (e.g. nm/um). The actual z-change per pixel depends on the field's physical pixel size.
- For leveling an unknown tilt, consider Plane Level instead, which automatically fits and removes the best-fit plane.
