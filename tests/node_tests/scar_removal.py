import numpy as np
from backend.node_registry import get_node_info
from tests.node_tests._shared import make_field


def test_scar_removal():
    from backend.nodes.scar_removal import ScarRemoval

    node = ScarRemoval()
    info = get_node_info("ScarRemoval")
    assert info["category"] == "Level & Correct"

    rows = 96
    cols = 128
    yy, xx = np.mgrid[0:rows, 0:cols]
    base = (
        0.005 * xx + 0.01 * yy
        + 0.12 * np.sin(2.0 * np.pi * xx / cols)
        + 0.07 * np.cos(2.0 * np.pi * yy / rows)
    )
    scarred = base.copy()
    scarred[24, 20:92] += 1.8
    scarred[25, 20:92] += 1.6
    scarred[60, 12:116] -= 1.7

    field = make_field(data=scarred)
    corrected, scar_mask, stats = node.process(
        field, scar_type="both", threshold_high=0.6, threshold_low=0.2, min_length=12, max_width=4,
    )

    mask_bool = scar_mask > 127
    assert scar_mask.dtype == np.uint8
    assert scar_mask.shape == field.data.shape
    assert np.count_nonzero(mask_bool) > 0
    assert np.count_nonzero(mask_bool[24:26, 20:92]) > 0
    assert np.count_nonzero(mask_bool[60:61, 12:116]) > 0
    assert np.allclose(corrected.data[~mask_bool], field.data[~mask_bool])

    stats_by_name = {row["quantity"]: row for row in stats}
    assert set(stats_by_name) == {"Scar pixels", "Scar fraction"}
    assert all(set(row) == {"quantity", "value", "unit"} for row in stats)
    assert stats_by_name["Scar pixels"]["unit"] == "px"
    assert stats_by_name["Scar pixels"]["value"] == int(np.count_nonzero(mask_bool))
    assert stats_by_name["Scar fraction"]["value"] == float(
        np.count_nonzero(mask_bool) / mask_bool.size
    )

    before_rmse = np.sqrt(np.mean((field.data[mask_bool] - base[mask_bool]) ** 2))
    after_rmse = np.sqrt(np.mean((corrected.data[mask_bool] - base[mask_bool]) ** 2))
    assert after_rmse < before_rmse * 0.35

    clean_corrected, clean_mask, clean_stats = node.process(
        make_field(data=base), scar_type="both", threshold_high=0.6, threshold_low=0.2, min_length=12, max_width=4,
    )
    assert np.count_nonzero(clean_mask) == 0
    assert np.allclose(clean_corrected.data, base)
    clean_by_name = {row["quantity"]: row for row in clean_stats}
    assert clean_by_name["Scar pixels"]["value"] == 0
