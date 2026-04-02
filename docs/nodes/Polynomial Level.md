# Polynomial Level

Fit and subtract a polynomial background of given degree in x and y. Equivalent to gwy_data_field_fit_polynom.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to level |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with polynomial background subtracted |
| background | DATA_FIELD | The fitted polynomial background surface |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| degree_x | INT | 2 | Polynomial degree in the x direction (0–5) |
| degree_y | INT | 2 | Polynomial degree in the y direction (0–5) |

## Notes

- High polynomial degrees (> 4) may overfit and introduce artificial long-range modulation.
- No masking support; all pixels contribute equally to the fit.
