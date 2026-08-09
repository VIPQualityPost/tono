# MFM Lift Shift

Shifts a magnetic field image to a different lift height above the surface using the FFT-based transfer function exp(−2π|k|·Δz).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input MFM field (e.g. Hz in A/m) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| shifted | DATA_FIELD | Field propagated to the new lift height |
| measurement | RECORD_TABLE | The effective lift shift applied (in m) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shift_z | FLOAT | 10e-9 | Lift-height change Δz in metres; positive moves away from the surface |

## Notes

- Each spatial frequency |k| (cycles per metre) is attenuated by exp(−2π|k|·Δz), exactly as in the unshifted FFT arrangement. The DC component (transfer function 1) is preserved, so the mean value is unchanged.
- Δz is equivalent to new_lift − old_lift. A positive shift produces the field at a larger lift height (blurred); a negative shift sharpens the field towards the surface and grows exponentially with |k|, so it is generally only useful for moderate values and smooth data.
- The value unit of the input (e.g. A/m) is preserved; the result is the same physical quantity at a different height.
