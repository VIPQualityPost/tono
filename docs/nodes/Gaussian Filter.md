# Gaussian Filter

Apply a Gaussian blur to a DATA_FIELD. Equivalent to gwy_data_field_filter_gaussian.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field to filter |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| filtered | DATA_FIELD | Gaussian-blurred field |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| sigma | FLOAT | 1.0 | Standard deviation of the Gaussian kernel in pixels (0.01-50.0) |

## Notes

- sigma is specified in pixels, not physical units; the effective physical blur depends on pixel size.
- Large sigma values (> ~20 pixels) are slow due to the large kernel.
