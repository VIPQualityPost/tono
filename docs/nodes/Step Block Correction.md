# Step Block Correction

Correct vertical steps in scan lines block-by-block, without any line correction. Discontinuities between consecutive scan lines whose magnitude exceeds the threshold times the RMS vertical difference are located, blocks are built from the resulting marks, and each block's rows are shifted by the trimmed mean of the step. Ported from Gwyddion's blockstep module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with staircase/terrace steps between scan lines |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Field with the detected block steps removed |
| stats | RECORD_TABLE | Detected-block count plus the estimated step, row and split column of every block |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| threshold | FLOAT | 2.0 | Discontinuity threshold as a multiple of the RMS vertical difference between rows (0.1-10) |
| scan_direction | dropdown | left_to_right | Scanning direction of the acquisition: left to right or right to left |

## Notes

- The threshold is multiplied by the RMS vertical difference (mean over rows of the RMS row slope, i.e. the tan(beta0) line statistic, times the pixel height) before comparing with the inter-row jumps.
- A marker is placed where a jump between two rows exceeds the threshold; blocks are formed from scan-row splits whose combined mark coverage reaches 3/4 of the row width, and blocks on consecutive lines are merged keeping the better-scoring one.
- The step of every block is the trimmed mean (a quarter of the row width discarded on each side) of the row differences across the block's two complementary horizontal segments.
- Thresholds far above the actual steps leave the field unchanged (zero detected blocks).
