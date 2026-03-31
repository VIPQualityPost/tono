# Histogram

Compute the height distribution histogram (DH). Use log scale to reveal small peaks next to a dominant background. Outputs marker measurements while showing the histogram interactively in-node. Equivalent to gwy_data_field_dh.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| measurements | RECORD_TABLE | Measurements at the two cursor markers (x/y positions and dx/dy) |
| marker_pair | COORDPAIR | Current cursor marker positions |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_bins | INT | 256 | Number of histogram bins (10–1000) |
| y_scale | dropdown | linear | Y-axis scale: linear or log |

## Limitations

- Cursor positions are stored as fractions of the histogram range and are set interactively.
- Log scale displays bins as log(count); bins with zero count appear as the minimum log value.
