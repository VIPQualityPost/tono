import numpy as np
from tests.node_tests._shared import make_field


def _grating_field():
    """Tilted plane + vertical bars + pits on alternating rows + per-row DC offsets."""
    N = 128
    y, x = np.mgrid[0:N, 0:N] / N
    plane = 40.0 * x - 20.0 * y
    bars = np.zeros((N, N))
    for i in range(0, N, 16):
        bars[:, i:i+8] = 40.0
    pits = np.zeros((N, N))
    for j in range(1, N, 2):
        # pits fully inside the land strips (8..16, 24..32, ...) so the
        # bar/land mix of usable pixels is identical on every row
        for k in range(9, N, 16):
            pits[j, k:k+6] = -80.0
    row_offset = 30.0 * np.sin(2 * np.pi * np.arange(N) / 17.0)
    data = plane + bars + pits + row_offset[:, None]
    mask = np.zeros((N, N), dtype=np.uint8)
    mask[pits < 0] = 255
    return make_field(data=data, shape=(N, N)), bars, mask


def test_flatten_reconstructs_grating():
    """Masked plane fit + row alignment puts landing rows and inter-pit areas
    on one level, recovering a flat grating despite per-row DC offsets."""
    from backend.nodes.flatten import FlattenField
    node = FlattenField()

    field, bars, mask = _grating_field()
    leveled, plane = node.process(field, masking="exclude", mask=mask)

    exp = mask == 0
    landing_rows = ~(mask > 0).any(axis=1)
    landing_levels = [np.median(leveled.data[j, exp[j, :]]) for j in np.where(landing_rows)[0]]
    interpit_levels = [
        np.median(leveled.data[j, exp[j, :]])
        for j in np.where(~landing_rows)[0]
        if exp[j, :].any()
    ]
    assert abs(float(np.mean(landing_levels) - np.mean(interpit_levels))) < 1e-6

    # bars persist and stay at one level on rows with identical geometry
    bar_levels = [
        np.median(leveled.data[j, (bars[j, :] > 0) & (mask[j, :] == 0)])
        for j in np.where(landing_rows)[0]
    ]
    land_levels = [
        np.median(leveled.data[j, (bars[j, :] == 0) & (mask[j, :] == 0)])
        for j in np.where(landing_rows)[0]
    ]
    assert np.std(bar_levels) < 1e-6
    assert abs(float(np.mean(bar_levels) - np.mean(land_levels)) - 40.0) < 2.0


def test_flatten_aligns_rows_without_mask():
    """Even without a mask, per-row DC offsets are removed after the plane fit."""
    from backend.nodes.flatten import FlattenField
    node = FlattenField()

    N = 64
    y, x = np.mgrid[0:N, 0:N] / N
    data = 100 * x + 50 * y
    row_offset = 40.0 * np.sin(2 * np.pi * np.arange(N) / 9.0)
    field = make_field(data=data + row_offset[:, None])

    leveled, plane = node.process(field)
    row_medians = np.median(leveled.data, axis=1)
    assert np.std(row_medians) < 1e-6
    rows = {row["quantity"]: row for row in plane}
    assert set(rows) == {"Plane offset", "Tilt X", "Tilt Y"}
