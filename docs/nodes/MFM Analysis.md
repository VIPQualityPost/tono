# MFM Analysis

Magnetic Force Microscopy analysis: convert between MFM phase/force gradient and magnetic field quantities using Fourier-domain transfer functions.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input MFM data (phase, force gradient, or field) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Converted MFM quantity |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | phase_to_force_gradient | Conversion: phase_to_force_gradient, force_gradient_to_field, charge_density, magnetisation |
| lift_height | FLOAT | 50e-9 | Tip-sample separation in metres |

## Notes

- **phase_to_force_gradient**: Convert MFM phase shift to force gradient using the cantilever spring constant relationship.
- **force_gradient_to_field**: Recover the magnetic field from force gradient data via Fourier-domain deconvolution. Output unit: A/m.
- **charge_density**: Compute effective magnetic charge density. Output unit: A/m².
- **magnetisation**: Recover magnetisation from field data.
- All operations use the lift height to set the correct spatial frequency transfer function.
