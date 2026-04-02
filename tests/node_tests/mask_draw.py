import json
import numpy as np
from tests.node_tests._shared import make_field


def test_draw_mask():
    from backend.nodes.mask_draw import DrawMask
    node = DrawMask()

    field = make_field(data=np.zeros((32, 32), dtype=np.float64))
    from backend.execution_context import execution_callbacks, active_node
    overlays = []
    with execution_callbacks(overlay=lambda nid, data: overlays.append(data)), active_node("test"):
        mask_paths = [{"size": 5, "points": [{"x": 0.2, "y": 0.5}, {"x": 0.8, "y": 0.5}]}]

        mask, = node.process(field, pen_size=2, invert=False, mask_paths=json.dumps(mask_paths))
        assert mask.dtype == np.uint8
        assert mask.shape == (32, 32)
        assert mask[16, 16] == 255
        assert mask[14, 16] == 255
        assert mask[0, 0] == 0

        assert len(overlays) == 1
        assert overlays[0]["kind"] == "mask_paint"
        assert overlays[0]["section_title"] == "Mask"
        assert overlays[0]["image"].startswith("data:image/png;base64,")
        assert overlays[0]["image_width"] == field.xres
        assert overlays[0]["image_height"] == field.yres
        assert overlays[0]["invert"] is False

        inverted, = node.process(field, pen_size=2, invert=True, mask_paths=json.dumps(mask_paths))
        assert inverted[16, 16] == 0
        assert inverted[0, 0] == 255
        assert overlays[-1]["invert"] is True

        cleared, = node.process(field, pen_size=12, invert=False, mask_paths="[]")
        assert np.count_nonzero(cleared) == 0
