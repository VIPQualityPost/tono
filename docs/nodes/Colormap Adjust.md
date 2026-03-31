# Colormap Adjust

Adjust how a DATA_FIELD maps into its colormap without changing the underlying data. offset and scale operate in normalized display coordinates; Auto resets to the full data range.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field whose colormap mapping is adjusted |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Field with updated display_offset and display_scale metadata |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| offset | FLOAT | 0.0 | Shift the colormap center in normalized units (−1 to 1) |
| scale | FLOAT | 1.0 | Zoom the colormap range (0.05–4.0); values below 1 stretch contrast |
| auto | BUTTON | — | Reset offset to 0 and scale to 1 (full data range) |

## Limitations

- Only the display mapping metadata is changed; raw data values are unaffected.
- Scale must be positive and finite; zero or negative values raise an error.
