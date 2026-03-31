# Line Correction

Correct scan-line mismatches using Gwyddion-derived row alignment methods. Supports median and trimmed row alignment, difference-based alignment, polynomial row leveling, and step-line correction from Gwyddion's linecorrect/linematch modules.

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
| method | dropdown | median | Alignment method: median, median_diff, trimmed_mean, trimmed_diff, polynomial, or step |
| direction | dropdown | horizontal | Direction of scan lines to correct: horizontal or vertical |
| masking | dropdown | ignore | How to use the mask: ignore, include (correct using masked rows only), or exclude |
| trim_fraction | FLOAT | 0.05 | Fraction of extreme values to trim; visible only for trimmed_mean and trimmed_diff methods (0–0.5) |
| polynomial_degree | INT | 1 | Polynomial degree for the polynomial method (0–5); visible only for polynomial method |

## Limitations

- The step method is designed for step-like scan artifacts and may over-correct smooth surfaces.
- Mask shape must match the field shape if a mask is connected.
