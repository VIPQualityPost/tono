# Unrotate

Auto-detect and correct in-plane scan rotation. Computes a slope angle histogram, finds the dominant feature direction for the given symmetry, and rotates the image to align features with the axes.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to correct |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with rotation corrected |
| angle | FLOAT | Detected correction angle in degrees (applied rotation) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| symmetry | dropdown | 4-fold | Expected symmetry of the surface features: 2-fold, 3-fold, 4-fold, or 6-fold |

## Notes

- Best suited for crystalline or patterned surfaces where features have a clear preferred direction.
- 4-fold symmetry is the most common choice for cubic crystal surfaces and rectangular gratings.
- If the detected rotation is less than 0.01°, the data is returned unchanged.
- Uses bilinear interpolation; edges are handled with nearest-neighbor extension.
