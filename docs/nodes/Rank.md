# Rank

Presentation transform that enhances local contrast by replacing each pixel with a statistic of its neighborhood. The neighborhood is the ellipse inscribed in a square kernel of side `2*size + 1`. The result is min-max normalized to [0, 1] and is unitless.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to transform |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| rank | DATA_FIELD | Rank/presentation-transformed field, normalized to [0, 1], unitless |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| size | INT | 15 | Kernel size: the elliptic window is inscribed in a square of side 2*size+1 pixels (1--129) |
| filter_type | dropdown | rank | rank: fraction of window pixels not exceeding the center value; range: local max - min; normalization: (v - min)/(max - min) |

## Notes

- With `rank`, ties with the center value count with weight 1/2, so the result is the fraction of the window strictly below the center plus half the ties -- a local percentile. Near the field borders the window is truncated (fewer pixels are included), never padded.
- `range` and `normalization` use the same elliptic support; for a window whose values are all equal the normalization output is 0.5 (standard convention) before the final min-max normalization.
- The final output is always scaled so the minimum is 0 and the maximum is 1; a constant input produces all zeros. The height unit of the input is dropped (`si_unit_z` becomes empty).
- Implements the local rank computation with `range`/`normalization` output modes followed by min-max normalization; the elliptic kernel is filled via an elliptic-area routine.
