import numpy as np
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_watershed_segmentation():
    from scipy.ndimage import label
    from backend.nodes.watershed_segmentation import WatershedSegmentation

    node = WatershedSegmentation()
    y, x = np.mgrid[-1:1:64j, -1:1:64j]
    data = (
        2.0 * np.exp(-((x + 0.45) ** 2 + y**2) / 0.05)
        + 2.0 * np.exp(-((x - 0.45) ** 2 + y**2) / 0.05)
        - 0.3 * np.exp(-(x**2 + y**2) / 0.12)
    )
    field = make_field(data=data, xreal=2.0e-6, yreal=2.0e-6)

    previews = []
    with execution_callbacks(preview=lambda nid, uri: previews.append(uri)), active_node("test"):
        mask, = node.process(
            field,
            invert_height=False,
            locate_steps=10,
            locate_threshold=8,
            locate_drop_size=0.1,
            watershed_steps=20,
            watershed_drop_size=0.1,
            combine_mode="replace",
        )
    assert mask.dtype == np.uint8
    assert mask.shape == field.data.shape
    assert len(previews) == 1
    assert previews[0].startswith("data:image/png;base64,")

    _, ngrains = label(mask > 127)
    assert ngrains >= 2

    seed_mask = np.zeros_like(mask)
    seed_mask[:, :32] = 255
    intersected, = node.process(
        field,
        invert_height=False,
        locate_steps=10,
        locate_threshold=8,
        locate_drop_size=0.1,
        watershed_steps=20,
        watershed_drop_size=0.1,
        combine_mode="intersection",
        mask=seed_mask,
    )
    assert np.count_nonzero(intersected) < np.count_nonzero(mask)
    assert np.all(intersected[:, 40:] == 0)
