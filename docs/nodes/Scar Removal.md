# Scar Removal

Detect and remove horizontal scan scars using scar marking thresholds, then interpolate over the detected mask with a Laplace-style inpaint.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with scan scars |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Field with scars removed and interpolated |
| mask | IMAGE | Binary mask of the detected scar pixels |
| stats | RECORD_TABLE | Scar pixel count and fraction of the image |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| scar_type | dropdown | both | Which scar polarity to detect: both, positive (bright), or negative (dark) |
| threshold_high | FLOAT | 0.666 | High threshold relative to local RMS for strong scar detection (0-2) |
| threshold_low | FLOAT | 0.25 | Low threshold for extending already-detected scars (0-2) |
| min_length | INT | 16 | Minimum horizontal run length in pixels to classify as a scar (1-4096) |
| max_width | INT | 4 | Maximum vertical width in pixels for a scar candidate (1-32) |

## Notes

- Designed for horizontal (fast-scan) scars only; vertical scars are not detected.
- Aggressive thresholds may remove legitimate surface features that resemble scars.
