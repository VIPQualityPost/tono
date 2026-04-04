# Lateral Force Simulation

Simulate lateral (friction) force signals from topography data, modeling how the local surface slope affects the cantilever torsion signal in contact-mode AFM. Equivalent to Gwyddion's `latsim.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topography surface field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| forward | DATA_FIELD | Lateral force signal for the forward (+x) scan direction, in Newtons |
| reverse | DATA_FIELD | Lateral force signal for the reverse (-x) scan direction, in Newtons |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| direction | dropdown | forward | Scan direction to compute: forward, reverse, or both. When set to forward or reverse, both outputs carry the same single-direction result |
| friction_coefficient | FLOAT | 0.3 | Coulomb friction coefficient between tip and sample (0.0-10.0) |
| adhesion | FLOAT | 1e-9 | Tip-sample adhesion force in Newtons (0.0-1e-6) |
| load | FLOAT | 10e-9 | Applied normal load on the cantilever in Newtons (1e-12-1e-6) |

## Notes

- The lateral force is computed from a contact-mechanics model where the measured torsion signal depends on the local surface tilt angle. The x-gradient of the topography gives the slope, and the resulting lateral force combines the gravitational component along the slope with the friction force (proportional to the normal component of load plus adhesion): F_lateral = (F_load sin(theta) + mu (F_load cos(theta) + F_adhesion)) / (cos(theta) - mu sin(theta)).
- Forward and reverse scans produce different lateral force signals because friction opposes the scan direction. The forward scan (+x) adds the friction contribution to the slope component, while the reverse scan (-x) subtracts it, producing the characteristic "friction loop" seen in LFM experiments.
- Typical friction coefficients for common AFM sample materials: mica ~0.1-0.3, silicon ~0.2-0.5, polymers ~0.3-0.8, metals ~0.3-0.6. Use lower values for atomically smooth or lubricated surfaces.
- Output values represent the lateral force on the cantilever tip in Newtons. To convert to photodetector voltage, divide by the lateral sensitivity of the optical lever system.
- This node is the equivalent of Gwyddion's `latsim.c` lateral force simulation and uses the same contact-mechanics formulation for topography-induced friction artifacts.
