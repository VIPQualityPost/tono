# Grain Analysis

Label connected grain regions in a binary mask and compute per-grain statistics: area, equivalent diameter, mean/max height, bounding box. Equivalent to Gwyddion's grain statistics tools.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Height field providing z values for per-grain statistics |
| mask | IMAGE | Yes | Binary mask defining grain regions (white = grain) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| grain_stats | DATA_TABLE | Per-grain table with area, equivalent diameter, mean/max height, bounding box, and centroid |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| min_size | INT | 10 | Minimum grain area in pixels; smaller connected regions are ignored (1–100000) |

## Limitations

- Grain detection uses 2D connected-component labeling on the binary mask; the field and mask must have the same pixel dimensions.
- Physical area and diameter values require the field to carry valid physical calibration (xreal, yreal, si_unit_xy).
