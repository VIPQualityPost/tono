# Scan Line Reorder

Fix scan line ordering artifacts from meander (serpentine) scanning, interlacing, or inverted scan direction. Equivalent to Gwyddion's reorder.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input field with scan line artifacts |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Field with corrected scan line order |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | reverse_odd | Operation: reverse_odd, reverse_even, deinterlace_odd, deinterlace_even, flip_vertical |

## Notes

- **reverse_odd / reverse_even**: Reverse alternate rows to correct meander (serpentine/boustrophedon) scanning. Most SPM controllers scan left-to-right on odd lines and right-to-left on even lines; reversing odd rows fixes this.
- **deinterlace_odd / deinterlace_even**: Keep only odd or even rows and stretch to fill the original height. Useful when alternate scan lines were acquired under different conditions.
- **flip_vertical**: Reverse the row order (top becomes bottom). Useful when the scan direction is inverted.
- Apply this node before Line Correction for best results.
