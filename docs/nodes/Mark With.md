# Mark With

Create or modify a binary mask from the point-wise comparison of two data fields. Relational operations mark pixels where the condition between the two fields holds; arithmetic operations mark pixels where the combined value is non-zero. Equivalent to the mask-arithmetic semantics of Gwyddion's mark_with.c (data mapped to a mask via a value condition).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | First data field; defines the resolution of the mask |
| field_b | DATA_FIELD | Yes | Second data field, compared with field_a element-wise |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Binary mask (0/255 uint8): 255 where the condition holds |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | == | Point-wise condition: relational (==, !=, <, <=, >, >=) operations mark pixels where the relation between field_a and field_b holds; arithmetic (+, -, *, /, min, max) operations mark pixels where the combined value is non-zero |
| invert_mask | BOOLEAN | False | Invert the resulting mask, swapping marked and unmarked pixels |

## Notes

- Both fields must have identical resolution; otherwise the node raises an error.
- Comparisons are exact floating-point comparisons, matching Gwyddion's mask thresholding behaviour.
- Division follows IEEE semantics (x/0 gives infinity, 0/0 gives NaN), which are non-zero and therefore marked.
