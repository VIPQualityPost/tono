# Blind Tip Estimate

Blind tip estimation from a measured SPM image using the Villarrubia algorithm. Iteratively refines the tip shape using only the sharpest image features without knowing the true surface in advance.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Measured SPM surface image |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| tip | DATA_FIELD | Estimated tip shape (apex = maximum value, edges = 0) |
| certainty | IMAGE | Map marking surface pixels where the tip was in unambiguous single contact |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_pixels | INT | 33 | Tip grid size in pixels (odd values only, 3-129) |
| threshold | FLOAT | 0.0 | Noise floor in metres; increase if the estimated tip is unrealistically sharp |
| method | dropdown | partial | partial: uses local maxima only (faster, needs sharp isolated features); full: uses all points above morphological opening (slower, more robust) |
| use_edges | BOOLEAN | False | When enabled, also uses image edge pixels as refinement candidates |

## Notes

- Requires sharp, isolated features on the surface for reliable results.
- Output tip has the same pixel size as the input field; tip deconvolution requires matching pixel sizes.
- Large tip sizes (n_pixels > ~65) or the full method on large images can be slow.
- Equivalent to gwy_tip_estimate_partial / gwy_tip_estimate_full + gwy_tip_cmap.
