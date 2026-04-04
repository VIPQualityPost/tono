# Flatten Base

Level the flat base of a surface that has raised features (particles, grains). Uses a height percentile threshold to identify base pixels, fits a polynomial to those pixels, and subtracts it. Unlike plane level, this ignores tall features that would bias the fit. Equivalent to Gwyddion's flatten_base.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with raised features on a tilted base |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| leveled | DATA_FIELD | Field with base leveled |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| threshold_percentile | FLOAT | 30.0 | Height percentile below which pixels are considered base (5-80) |
| poly_degree | INT | 2 | Polynomial degree for base fit: 0 = constant, 1 = plane, 2 = quadratic (0-5) |

## Notes

- Set the threshold percentile so that it includes most of the base but excludes the features. For sparse particles on a flat substrate, 20-40% typically works well.
- poly_degree=1 is equivalent to plane leveling on the base only. Use 2-3 for curved substrates.
- If the features dominate the surface (>50% coverage), this node may not give good results — consider Median Background instead.
