# Resample

Resample a DATA_FIELD to a new pixel resolution while preserving physical dimensions. Physical size (xreal, yreal) is unchanged; pixel size dx/dy scales accordingly. Equivalent to gwy_data_field_new_resampled.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to resample |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| resampled | DATA_FIELD | Resampled field at the new resolution |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| width | INT | 256 | Output pixel width (2–16384) |
| height | INT | 256 | Output pixel height (2–16384) |
| interpolation | dropdown | linear | Interpolation method: linear, cubic, or nearest |

## Limitations

- Physical dimensions are preserved; upsampling does not add new information.
- Very large output sizes (e.g. 16384×16384) require substantial memory.
