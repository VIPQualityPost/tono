# Convolve

Convolve two images: each output pixel is the sum of the product of field_a with the reversed field_b kernel, computed with FFT convolution. This mirrors Gwyddion's Convolve process (modules/process/convolve.c), which places the kernel centred on the output pixel with a zero-filled exterior (the default "Zero" exterior type). Mode selects the output extent.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First input field (the image) |
| field_b | DATA_FIELD | Yes | Second input field (the kernel) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| convolved | DATA_FIELD | Convolution result with extents depending on mode |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | same | Output extent: full (Na+Nb-1), same (same resolution as field_a), or valid (overlap-only region, field_b must be smaller than field_a) |

## Notes

- Values are discrete convolution sums (Gwyddion's `as_integral` option is not exposed); the value unit of the output is the product of the two input value units, as in Gwyddion.
- In "same" mode the output keeps field_a's resolution and physical extents. In "full" and "valid" modes the pixel size of field_a is preserved and the physical extents scale proportionally with the output resolution (the same convention as the Cross-Correlate node); offsets are kept from field_a.
- In "valid" mode the node raises an error when field_b is larger than field_a since the overlap would be empty.
- Very different field sizes can make "full" mode output large; the FFT convolution is exact up to floating-point rounding.
