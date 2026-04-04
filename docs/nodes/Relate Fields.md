# Relate Fields

Fit a functional relationship between two data fields: b = f(a). Outputs the predicted field_b from the fit and a table of fitted parameters with R-squared goodness-of-fit. Equivalent to Gwyddion's relate.c module.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field_a | DATA_FIELD | Yes | Independent variable field |
| field_b | DATA_FIELD | Yes | Dependent variable field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| predicted | DATA_FIELD | Predicted field_b values from the fitted function |
| fit_params | RECORD_TABLE | Fitted coefficients and R-squared statistic |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| function | dropdown | linear | Functional form to fit: linear, quadratic, cubic, power, or logarithmic |

## Notes

- **Linear**: b = slope * a + intercept. Reports slope and intercept.
- **Quadratic**: b = a2*a^2 + a1*a + a0. Reports a2, a1, a0.
- **Cubic**: b = a3*a^3 + a2*a^2 + a1*a + a0. Reports a3, a2, a1, a0.
- **Power**: b = c * a^n (fitted via log-log regression). Reports exponent and coefficient. Requires positive values in both fields.
- **Logarithmic**: b = log_coeff * log(a) + intercept. Requires positive values in field_a.
- R-squared is always reported as the last row: values near 1.0 indicate a good fit.
- Both fields are flattened and truncated to the shorter length when they differ in total pixel count.
- The predicted output retains field_b's shape and metadata.
