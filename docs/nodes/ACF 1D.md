# ACF 1D

Compute the one-dimensional autocorrelation function of a line profile. Only positive lags are output on the x-axis. The measurement table reports the dominant period from the first positive peak.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| profile | LINE | Yes | Input line profile |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| acf | LINE | Autocorrelation function (positive lags only) |
| measurement | RECORD_TABLE | Table with the dominant peak period |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| level | dropdown | mean | Pre-processing: subtract mean before correlation, or none |

## Notes

- Only one-sided (positive lag) ACF is returned.
- Peak period detection finds only the first local maximum; multi-periodic signals report only the shortest detected period.
