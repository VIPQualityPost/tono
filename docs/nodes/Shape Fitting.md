# Shape Fitting

Fit a geometric primitive (sphere, paraboloid, or cylinder) to the surface data. Outputs either the fitted surface or the residual. Reports fitted parameters including radius of curvature, centre position, etc.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input surface |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | DATA_FIELD | Fitted surface or residual (original minus fit) |
| parameters | RECORD_TABLE | Fitted parameters and RMS residual |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| shape | dropdown | sphere | Geometric primitive: sphere, paraboloid, or cylinder |
| output | dropdown | residual | Output mode: residual (deviations from fit) or fitted (the fit itself) |

## Notes

- **Sphere**: Fits z = z0 - sqrt(R² - (x-cx)² - (y-cy)²). Reports centre (cx, cy), apex height (z0), and radius R.
- **Paraboloid**: Fits z = z0 + a(x-cx)² + b(y-cy)². Reports centre, apex, and curvature coefficients a, b.
- **Cylinder**: Fits a parabolic profile along one axis. Reports radius, curvature, and cylinder orientation angle.
- The residual output is useful for evaluating fit quality — a good fit produces small, random residuals.
