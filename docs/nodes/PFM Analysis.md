# PFM Analysis

Compute polarization vectors from Piezoresponse Force Microscopy (PFM) data by combining vertical (VPFM) and lateral (LPFM) amplitude and phase channels into polarization magnitude, azimuth, and inclination maps.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| vpfm_amplitude | DATA_FIELD | Yes | Vertical PFM amplitude channel |
| lpfm_amplitude | DATA_FIELD | Yes | Lateral PFM amplitude channel |
| vpfm_phase | DATA_FIELD | Yes | Vertical PFM phase channel (radians) |
| lpfm_phase | DATA_FIELD | Yes | Lateral PFM phase channel (radians) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| magnitude | DATA_FIELD | Polarization vector magnitude |
| azimuth | DATA_FIELD | In-plane polarization angle |
| inclination | DATA_FIELD | Out-of-plane polarization angle (3D mode only) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| mode | dropdown | 2d | Decomposition mode: 2d (in-plane only) or 3d (full polarization vector) |
| lateral_sensitivity | FLOAT | 1.0 | Scale factor applied to the lateral signal to compensate for differing VPFM/LPFM detector sensitivities |

## Notes

- PFM measures the local piezoelectric response of ferroelectric materials by detecting surface deformation under an applied AC bias via the AFM cantilever.
- In **2d** mode, only in-plane polarization is resolved from the LPFM channels; magnitude and azimuth are computed but inclination is not produced. In **3d** mode, both vertical and lateral channels are combined to reconstruct the full polarization vector, including inclination.
- The **lateral_sensitivity** parameter compensates for the fact that vertical and lateral deflection detectors typically have different sensitivities. Set this to the ratio of LPFM to VPFM detector sensitivity for accurate vector reconstruction.
- Phase inputs must be in radians. If your data is in degrees, convert before connecting (multiply by pi/180).
- Amplitude channels should be unsigned (absolute) piezoresponse magnitudes; the phase channels encode the sign (direction) of the polarization.
