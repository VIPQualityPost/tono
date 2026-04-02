# Field Arithmetic

Apply a point-wise arithmetic operation to two DATA_FIELDs of the same resolution. Equivalent to gwy_data_field_sum_fields / subtract_fields / multiply_fields / divide_fields / min_of_fields / max_of_fields / hypot_of_fields.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First operand |
| field_b | DATA_FIELD | Yes | Second operand |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Result of the arithmetic operation (inherits metadata from field_a) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | add | Element-wise operation: add, subtract, multiply, divide, min, max, or hypot (√(a²+b²)) |

## Notes

- Both fields must have exactly the same pixel dimensions; mismatched sizes raise an error.
- divide may produce NaN or Inf pixels where field_b is zero.
