import numpy as np
from backend.data_types import DataField
from tests.node_tests._shared import make_field


def test_facet_level():
    from backend.node_registry import get_node_info
    from backend.nodes.level_facet import FacetLevelField
    from backend.nodes.level_plane import PlaneLevelField

    def fit_pixel_plane(data, region):
        yy, xx = np.mgrid[0:data.shape[0], 0:data.shape[1]]
        A = np.column_stack([np.ones(int(np.count_nonzero(region))), xx[region].astype(np.float64), yy[region].astype(np.float64)])
        coeffs, _, _, _ = np.linalg.lstsq(A, data[region].ravel().astype(np.float64), rcond=None)
        return float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

    node = FacetLevelField()
    plane_node = PlaneLevelField()
    assert get_node_info("FacetLevelField")["category"] == "Level & Correct"

    N = 96
    yy, xx = np.mgrid[0:N, 0:N]
    base = 0.055 * xx + 0.028 * yy
    terraces = np.zeros((N, N), dtype=np.float64)
    terraces[:, 54:] += 6.0
    terraces[18:70, 68:88] += 3.5
    field = make_field(data=base + terraces)

    plane_leveled, = plane_node.process(field)
    facet_leveled, = node.process(field, masking="ignore")

    left_region = xx < 48
    right_region = (xx > 60) & ~((yy >= 18) & (yy < 70) & (xx >= 68) & (xx < 88))
    _, plane_left_bx, plane_left_by = fit_pixel_plane(plane_leveled.data, left_region)
    _, plane_right_bx, plane_right_by = fit_pixel_plane(plane_leveled.data, right_region)
    _, facet_left_bx, facet_left_by = fit_pixel_plane(facet_leveled.data, left_region)
    _, facet_right_bx, facet_right_by = fit_pixel_plane(facet_leveled.data, right_region)
    plane_slope = float(max(np.hypot(plane_left_bx, plane_left_by), np.hypot(plane_right_bx, plane_right_by)))
    facet_slope = float(max(np.hypot(facet_left_bx, facet_left_by), np.hypot(facet_right_bx, facet_right_by)))
    assert facet_slope < plane_slope * 1e-6

    mask = np.zeros((N, N), dtype=np.uint8)
    mask[24:72, 24:72] = 255
    base_only = 0.035 * xx + 0.014 * yy
    masked_facet = 5.0 - 0.065 * xx + 0.045 * yy
    competing = np.where(mask > 0, masked_facet, base_only)
    competing_field = make_field(data=competing)

    excluded, = node.process(competing_field, masking="exclude", mask=mask)
    included, = node.process(competing_field, masking="include", mask=mask)

    outer_region = (mask == 0) & (xx > 4) & (xx < N - 4) & (yy > 4) & (yy < N - 4)
    inner_region = (mask > 0) & (xx > 28) & (xx < 68) & (yy > 28) & (yy < 68)
    _, excl_outer_bx, excl_outer_by = fit_pixel_plane(excluded.data, outer_region)
    _, excl_inner_bx, excl_inner_by = fit_pixel_plane(excluded.data, inner_region)
    _, incl_outer_bx, incl_outer_by = fit_pixel_plane(included.data, outer_region)
    _, incl_inner_bx, incl_inner_by = fit_pixel_plane(included.data, inner_region)

    assert float(np.hypot(excl_outer_bx, excl_outer_by)) < float(np.hypot(incl_outer_bx, incl_outer_by)) * 0.2
    assert float(np.hypot(incl_inner_bx, incl_inner_by)) < float(np.hypot(excl_inner_bx, excl_inner_by)) * 0.2

    bad_units = DataField(data=np.zeros((16, 16), dtype=np.float64), xreal=1e-6, yreal=1e-6, si_unit_xy="nm", si_unit_z="V")
    try:
        node.process(bad_units, masking="ignore")
    except ValueError as exc:
        assert "compatible XY and Z units" in str(exc)
    else:
        assert False, "Facet level should reject incompatible XY/Z units."
