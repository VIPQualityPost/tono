# Mask Operations

Apply boolean logic to two binary masks. Supports AND, OR, XOR, NAND, NOR, XNOR, directional subtraction (A minus B, B minus A), implication, pass-through, and constant true/false outputs.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mask_a | IMAGE | Yes | First binary mask operand |
| mask_b | IMAGE | Yes | Second binary mask operand |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| mask | IMAGE | Result of the boolean operation |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | and | Boolean operation: and, or, xor, xnor, nand, nor, a_minus_b, b_minus_a, a, b, not_a, not_b, a_implies_b, b_implies_a, false, true |

## Limitations

- Both masks must have the same pixel dimensions.
