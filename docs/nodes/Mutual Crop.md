# Mutual Crop

Align two images using FFT cross-correlation and crop both to their overlapping region. Useful for comparing images acquired at different times or with slight position offsets. Equivalent to Gwyddion's mcrop.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First input field |
| field_b | DATA_FIELD | Yes | Second input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| cropped_a | DATA_FIELD | Field A cropped to the overlapping region |
| cropped_b | DATA_FIELD | Field B cropped to the overlapping region |

## Controls

This node has no user-adjustable controls. Alignment is fully automatic.

## Notes

- Both fields are zero-padded to a common shape, mean-subtracted, and cross-correlated in the frequency domain to find the optimal shift.
- The overlap region is computed from the detected shift; both output fields are cropped to identical pixel dimensions.
- If no valid overlap is found (e.g. completely non-overlapping images), the original fields are returned unchanged.
- Physical dimensions (xreal, yreal) of the outputs are updated to reflect the cropped size using field_a's pixel spacing.
