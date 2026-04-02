import numpy as np
from tests.node_tests._shared import make_field


def test_threshold_mask():
    from backend.nodes.mask_threshold import ThresholdMask
    node = ThresholdMask()

    data = np.zeros((64, 64))
    data[:, 32:] = 1.0
    field = make_field(data=data)

    from backend.execution_context import execution_callbacks, active_node
    previews = []
    with execution_callbacks(preview=lambda nid, uri: previews.append(uri)), active_node("test"):
        mask, table = node.process(field, method="absolute", threshold=0.5, direction="above")
        assert mask.dtype == np.uint8
        assert mask.shape == (64, 64)
        assert np.all(mask[:, :32] == 0)
        assert np.all(mask[:, 32:] == 255)

        assert len(previews) == 1
        assert previews[0].startswith("data:image/png;base64,")

        mask_below, _ = node.process(field, method="absolute", threshold=0.5, direction="below")
        assert np.all(mask_below[:, :32] == 255)
        assert np.all(mask_below[:, 32:] == 0)

        mask_rel, _ = node.process(field, method="relative", threshold=0.5, direction="above")
        assert np.all(mask_rel[:, 32:] == 255)

        mask_otsu, _ = node.process(field, method="otsu", threshold=0.0, direction="above")
        assert mask_otsu[:, 32:].sum() > mask_otsu[:, :32].sum()


def test_threshold_mask_unknown_method():
    from backend.nodes.mask_threshold import ThresholdMask
    node = ThresholdMask()
    field = make_field(data=np.zeros((16, 16)))
    try:
        node.process(field, method="invalid", threshold=0.5, direction="above")
        assert False, "Expected ValueError"
    except ValueError:
        pass
