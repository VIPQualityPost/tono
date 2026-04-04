# Grain Summary

Compute aggregate statistics for all grains in a mask: count, density, coverage fraction, mean/median area, total volume, and height statistics. Equivalent to Gwyddion's grain_summary.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface data |
| mask | IMAGE | Yes | Binary mask defining grain regions |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| summary | RECORD_TABLE | Table of aggregate grain statistics |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| min_size | INT | 10 | Minimum grain size in pixels to include (1–100000) |

## Notes

- Reported statistics: grain count, grain density (count per unit area), coverage fraction, mean area, median area, total volume, mean height, median height, max area, min area.
- Volume is computed relative to the mean height of the non-grain background.
- Use Grain Analysis for per-grain statistics, or Grain Distributions for histograms.
