# Custom Convolution

Apply a user-defined convolution kernel to a DATA_FIELD. Enter rows of space-separated numbers. Equivalent to Gwyddion convolution_filter.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Filtered field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| kernel | STRING (multiline) | "0 -1 0\n-1 5 -1\n0 -1 0" | Kernel rows, each as space-separated numbers on a new line |
| normalize | BOOLEAN | True | Divide the result by the sum of absolute kernel values to preserve amplitude |
| boundary | dropdown | reflect | Boundary handling: reflect, nearest, or wrap |

## Notes

- Kernel must be a rectangle: all rows must have the same number of values.
- Maximum kernel size is 51×51; larger kernels are rejected.
- Non-finite values in the kernel are rejected and the input is returned unchanged.
- For large kernels, direct convolution can be slow; consider FFT Filter instead.
