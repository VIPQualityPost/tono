import numpy as np
from tests.node_tests._shared import make_field


def test_plane_level():
    from backend.nodes.level_plane import PlaneLevelField
    node = PlaneLevelField()

    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    signal = np.sin(2 * np.pi * 5 * x)
    data = 100 * x + 50 * y + signal
    field = make_field(data=data)

    result, = node.process(field)
    assert result.data.shape == field.data.shape
    assert abs(result.data.mean()) < 1e-10
    corr = np.corrcoef(result.data.ravel(), signal.ravel())[0, 1]
    assert corr > 0.98

    yy_px, xx_px = np.mgrid[0:N, 0:N]

    def fit_pixel_plane(data_in, region):
        A = np.column_stack([np.ones(int(np.count_nonzero(region))), xx_px[region].astype(np.float64), yy_px[region].astype(np.float64)])
        coeffs, _, _, _ = np.linalg.lstsq(A, data_in[region].ravel().astype(np.float64), rcond=None)
        return float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

    mask = np.zeros((N, N), dtype=np.uint8)
    mask[20:44, 22:46] = 255
    feature = np.zeros((N, N), dtype=np.float64)
    feature[mask > 0] = 35.0
    masked_field = make_field(data=100 * x + 50 * y + feature)

    unmasked, = node.process(masked_field)
    masked, = node.process(masked_field, masking="exclude", mask=mask)

    outside = mask == 0
    _, unmasked_bx, unmasked_by = fit_pixel_plane(unmasked.data, outside)
    _, masked_bx, masked_by = fit_pixel_plane(masked.data, outside)
    assert np.hypot(masked_bx, masked_by) < np.hypot(unmasked_bx, unmasked_by) * 1e-3
