# DWT Anisotropy

Quantify surface anisotropy using a multi-level 2-D Haar wavelet decomposition. At each decomposition level, horizontal and vertical detail energies are compared to produce an X/Y energy ratio. Equivalent to Gwyddion's dwtanisotropy.c.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| anisotropy_map | DATA_FIELD | Per-pixel anisotropy ratio map (averaged across decomposition levels) |
| statistics | RECORD_TABLE | Per-level X/Y detail energies, energy ratio, and anisotropy flag (quantity/value/unit rows) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| n_levels | INT | 4 | Number of wavelet decomposition levels (1--10) |
| ratio_threshold | FLOAT | 0.2 | Deviation from 1.0 required to flag a level as anisotropic (0.001--10.0) |

## Notes

- The decomposition uses the Haar wavelet (db1), which splits each 2x2 block into approximation (LL), horizontal detail (LH), vertical detail (HL), and diagonal detail (HH) coefficients.
- Energy ratios are computed as sum(HL^2) / sum(LH^2) at each level. HL captures horizontal features (edges running left-right), while LH captures vertical features (edges running top-bottom).
- Ratio > 1 means the surface has more horizontal features; ratio < 1 means more vertical features; ratio near 1 indicates isotropy.
- The input is padded to the next power of 2 if necessary; padding uses edge values.
- The anisotropy map is built by upsampling each level's per-pixel ratio and averaging across levels.
- The statistics table contains per-level rows with quantity/value/unit: X energy, Y energy, X/Y ratio, and the anisotropic flag (1.0 when |ratio - 1| exceeds ratio_threshold, else 0.0).
