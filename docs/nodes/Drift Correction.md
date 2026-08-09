# Drift Correction

Compensate for thermal or piezo drift between scan lines. Estimates inter-row displacement via cross-correlation and shifts rows to align them.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with drift artifacts |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| corrected | DATA_FIELD | Drift-corrected field |
| drift | RECORD_TABLE | Drift statistics: max, mean \|drift\|, and RMS drift in px, plus max drift in physical units along the corrected direction |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| reference | dropdown | previous_row | Reference for drift estimation: previous_row (local) or mean_row (global average) |
| direction | dropdown | horizontal | Drift direction to correct: horizontal or vertical |

## Notes

- Use previous_row for slow, cumulative drift. Use mean_row when drift is more random row-to-row.
- Apply after Line Correction for best results.
- Vertical direction transposes the correction axis — useful for column-scanned data.
