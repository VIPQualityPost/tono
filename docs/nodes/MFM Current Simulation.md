# MFM Current Simulation

Computes the magnetic stray field from an infinite current-carrying strip and the resulting force on an MFM tip. Useful for simulating the MFM response to current-carrying traces and interconnects.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Topography used for grid dimensions (x/y size and resolution) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| hx | DATA_FIELD | In-plane (x) magnetic field component (A/m) |
| hz | DATA_FIELD | Out-of-plane (z) magnetic field component (A/m) |
| force | DATA_FIELD | Vertical force on the MFM tip (N) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| height | FLOAT | 100e-9 | Tip-sample separation in metres |
| current | FLOAT | 1e-3 | Strip current in amperes |
| width | FLOAT | 100e-9 | Width of the current-carrying strip in metres |
| tip_magnetization | FLOAT | 1e5 | Effective tip magnetic moment per unit volume in A/m |

## Notes

- The current strip is infinite along y and centred at x = 0, so the field varies only in the x direction.
- Uses the Biot-Savart law for an infinite conducting strip of finite width to compute Hx and Hz.
- Hx is the in-plane field component; Hz is the out-of-plane component.
- Force is calculated with the point-dipole approximation: Fz = mu_0 * m_tip * dHz/dz.
- Useful for simulating MFM response to current-carrying traces/interconnects.
- Equivalent to Gwyddion's mfm_current.c.
