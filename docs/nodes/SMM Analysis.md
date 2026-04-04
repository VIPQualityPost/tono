# SMM Analysis

Scanning Microwave Microscopy analysis: perform 3-point calibration and de-embedding to convert raw S11 reflection coefficient measurements into quantitative tip-sample capacitance and impedance maps. Equivalent to Gwyddion's smm.c and smm_apply.c modules.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| s11_amplitude | DATA_FIELD | Yes | Measured S11 reflection coefficient amplitude |
| s11_phase | DATA_FIELD | Yes | Measured S11 reflection coefficient phase (radians) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| capacitance | DATA_FIELD | Calibrated tip-sample capacitance map (unit: F) |
| impedance_real | DATA_FIELD | Real part of the de-embedded tip-sample impedance (unit: Ohm) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| frequency | FLOAT | 1e9 | Microwave excitation frequency in Hz |
| ref_impedance | FLOAT | 50.0 | Reference impedance of the transmission line in Ohm |
| cal_c1 | FLOAT | — | First calibration capacitance standard (F) |
| cal_c2 | FLOAT | — | Second calibration capacitance standard (F) |
| cal_c3 | FLOAT | — | Third calibration capacitance standard (F) |
| cal_s11_1 | FLOAT | — | Measured S11 (complex magnitude) at the first calibration standard |
| cal_s11_2 | FLOAT | — | Measured S11 (complex magnitude) at the second calibration standard |
| cal_s11_3 | FLOAT | — | Measured S11 (complex magnitude) at the third calibration standard |

## Notes

- SMM measures local microwave impedance and capacitance by recording the S11 reflection coefficient of a scanning probe coupled to a vector network analyser (VNA) operating at GHz frequencies.
- The 3-point calibration procedure uses three known capacitance standards to solve for the VNA error terms and correct systematic measurement errors, mapping raw S11 values to the true tip-sample impedance.
- The error model decomposes VNA systematics into three terms: e00 (directivity), e01 (tracking), and e11 (source match). These are determined from the three calibration measurements and then used to de-embed every pixel.
- Calibration capacitances should span the expected measurement range; widely spaced standards yield a better-conditioned error model and more accurate results.
- The phase input must be in radians. If your data is in degrees, convert before connecting to this node.
