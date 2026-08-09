# Wrap Value

Rewrap periodic values in a DATA_FIELD to a specified angular or custom range. Commonly used for phase images where values should lie within a well-defined interval.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with periodic values to wrap |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| wrapped | DATA_FIELD | Field with values wrapped to the target range |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| preset | dropdown | 0-360 | Wrapping range preset: 0-360 (degrees), pm180 (±180°), 0-2pi (radians), pm_pi (±π), or custom |
| custom_min | FLOAT | 0.0 | Lower bound of the wrapping range (used only when preset is custom) |
| custom_max | FLOAT | 360.0 | Upper bound of the wrapping range (used only when preset is custom) |

## Notes

- Preset ranges: 0-360 wraps to [0, 360], pm180 wraps to [-180, 180], 0-2pi wraps to [0, 2π], pm_pi wraps to [-π, π].
- custom_min and custom_max are ignored unless preset is set to custom.
- This node applies modular arithmetic so that all output values fall within the chosen interval. It does not scale or rescale values.
- Particularly useful for MFM phase channels, Kelvin probe contact potential images, and interferometric phase maps.
