# Line Correction

Correct scan-line mismatches using row alignment methods. Supports median and trimmed row alignment, difference-based alignment, modus (most-common value) alignment, Gaussian-weighted row matching, polynomial row leveling, and step-line correction.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with scan-line artifacts |
| mask | IMAGE | No | Binary mask to include or exclude regions during correction |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Field with scan-line offsets removed |
| background | DATA_FIELD | Estimated per-line background that was subtracted |
| row_shifts | LINE | Per-row shift values applied during correction |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | median | Alignment method: median, median_diff, trimmed_mean, trimmed_diff, polynomial, modus, matching, or step |
| direction | dropdown | horizontal | Direction of scan lines to correct: horizontal or vertical |
| masking | dropdown | ignore | How to use the mask: ignore, include (correct using masked rows only), or exclude |
| trim_fraction | FLOAT | 0.05 | Fraction of extreme values to trim; visible only for trimmed_mean and trimmed_diff methods (0-0.5) |
| polynomial_degree | INT | 1 | Polynomial degree for the polynomial method (0-5); visible only for polynomial method |

## Notes

- The modus method estimates each row's most common value from the densest
  sample cluster and aligns rows to it; it suits data with dominant value
  levels (terraces, plateaus).
- The matching method (Gaussian-weighted, from linematch.c LINE_MATCH_MATCH)
  aligns consecutive rows through their locally similar slopes and accumulates
  the offsets; rows that are exact copies of their neighbors are left in
  place by the C algorithm and are then not shifted.
- The step method is designed for step-like scan artifacts and may over-correct smooth surfaces.
- Mask shape must match the field shape if a mask is connected.
