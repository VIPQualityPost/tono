# SEM Simulation

Simulate Scanning Electron Microscopy (SEM) secondary electron yield from topography data. Surface slopes and edges appear bright, while flat areas appear dark. Equivalent to Gwyddion's `semsim.c` module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input topography field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Simulated SEM image (dimensionless intensity) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| method | dropdown | integration | Simulation method: integration (fast, deterministic) or monte_carlo (stochastic) |
| sigma | FLOAT | 3.0 | Beam interaction distance in pixels, controlling the spatial resolution of the simulated interaction volume |
| n_samples | INT | 100 | Number of Monte Carlo samples per pixel (only used by the monte_carlo method) |

## Notes

- SEM imaging contrast arises because secondary electron yield depends on the local surface orientation relative to the incident beam. Tilted surfaces and sharp edges emit more secondary electrons and therefore appear brighter.
- The integration method evaluates yield analytically from local slopes, making it faster and fully deterministic. The Monte Carlo method samples random electron trajectories, introducing realistic statistical variation into the result.
- Sigma controls the effective size of the beam interaction volume. Larger values blur fine detail and simulate a broader excitation region; smaller values preserve sharp features.
- n_samples only affects the monte_carlo method. Higher values produce smoother, more converged images at the cost of longer computation time.
- This node is equivalent to Gwyddion's `semsim.c` data processing module.
