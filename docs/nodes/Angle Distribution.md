# Angle Distribution

Calculate the two-dimensional distribution of angle projections: for every pixel the local slope vector is projected onto a set of directions and the projections are accumulated into a polar histogram. This mirrors the Statistics &gt; Angle Distribution operation. The measurement table reports the mean, standard deviation and maximum of the local slope angle.

## Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| field | DATA_FIELD | Yes | Input height field |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| distribution | DATA_FIELD | 2-D histogram of slope-vector projections, axes from -pi to pi radians |
| measurement | RECORD_TABLE | Mean slope angle, standard deviation of the slope angle, and maximum slope angle (all in rad) |

## Controls

| Name | Type | Default | Description |
|------|------|---------|-------------|
| size | INT | 200 | Output resolution (size x size bins) |
| steps | INT | 360 | Number of projection directions used to accumulate the histogram |
| logscale | BOOLEAN | False | Display logarithmic counts: log(count) + 1 for non-empty bins, 0 otherwise |
| fit_plane | BOOLEAN | False | Compute slopes by fitting a local plane through each neighborhood instead of using simple differences |
| kernel_size | INT | 5 | neighborhood size for the local plane fitting; only used when fit_plane is on |

## Notes

- With fit_plane off, slopes are computed with symmetric differences (one-sided at edges), exactly as with the slope filter; the values are in physical units (height per metre).
- With fit_plane on, a plane is least-squares fitted through each clamped neighborhood. The fit is exact for centerd windows; edge windows reproduce the approximate edge behaviour.
- Every pixel deposits one vote per direction step, so the total histogram mass equals pixels x steps (before logscale).
- A perfectly flat image produces an all-zero distribution.
