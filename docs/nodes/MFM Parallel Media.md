# MFM Parallel Media

Simulates the stray field above an in-plane magnetised parallel medium: alternating stripes with left/right (in-plane) remanent magnetisation separated by gaps, the configuration of longitudinal magnetic recording media. Equivalent to Gwyddion's mfm_parallel module (gwy_data_field_mfm_parallel_medium).

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Grid template: only the lateral dimensions are used, the values are ignored |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| field | DATA_FIELD | Simulated stray-field component or tip force on the template grid |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| operation | dropdown | hz | Output quantity: hx (in-plane field), hz (vertical field), force (Fz from Hz), force_dz (Fz from dHz/dz), force_ddz (Fz from d²Hz/dz²) |
| probe | dropdown | point_charge | Tip model used for the force outputs: point_charge or bar |
| height | FLOAT | 100e-9 | Output plane height above the surface in metres |
| thickness | FLOAT | 100e-9 | Magnetic film thickness in metres |
| magnetization | FLOAT | 1e6 | Remanent magnetisation in A/m |
| size_a | FLOAT | 200e-9 | Width of the left-oriented stripes in metres |
| size_b | FLOAT | 200e-9 | Width of the right-oriented stripes in metres |
| size_c | FLOAT | 10e-9 | Gap width between stripes in metres |
| mtip | FLOAT | 1e3 | Tip magnetisation in A/m (bar probe) |
| bx | FLOAT | 10e-9 | Bar probe width in x in metres |
| by | FLOAT | 10e-9 | Bar probe width in y in metres |
| length | FLOAT | 500e-9 | Bar probe length (z extent) in metres |

## Notes

- Each stripe boundary contributes a closed-form Biot-Savart wall term; the medium is extended 20 × (a + b + t + h) beyond the field on both sides, so the result approximates an infinite periodic medium.
- hx is the in-plane field component; the y component is identically zero for this model.
- Force outputs: for the point-charge probe Fz = −μ₀·m_tip·b_x·b_y·Hz exactly; for the bar probe the force is computed by multiplying the field FFT with the probe transfer function c·sinc(kx·bx/2)·sinc(ky·by/2)·(1 − e^(−|k|·L)).
- Units: hx/hz in A/m, force in N, force_dz in N/m, force_ddz in N/m².
