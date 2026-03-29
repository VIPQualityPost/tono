import json
import numpy as np
from backend.data_types import DataField, ImageData, render_datafield_preview
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_markup():
    from backend.nodes.markup import Markup
    from backend.data_types import _preview_markup_stroke_width

    node = Markup()
    field = make_field(data=np.linspace(0.0, 1.0, 48 * 48, dtype=np.float64).reshape(48, 48))
    base = render_datafield_preview(field, field.colormap)
    required_inputs = Markup.INPUT_TYPES()["required"]

    assert _preview_markup_stroke_width(5, 128, 128) == 5
    assert _preview_markup_stroke_width(5, 2048, 2048) > 5
    assert required_inputs["input"][1]["accepted_types"] == ["DATA_FIELD", "IMAGE"]
    assert required_inputs["shape"][1]["default"] == "arrow"
    assert required_inputs["stroke_color"][1]["default"] == "#ff0000"

    overlays = []
    with execution_callbacks(overlay=lambda nid, data: overlays.append(data)), active_node("test"):
        plain_field, = node.process(input=field, shape="line", stroke_color="#ffd54f", stroke_width=3, markup_shapes="[]")
        assert isinstance(plain_field, DataField)
        assert plain_field.overlays[-1]["kind"] == "markup"
        plain = render_datafield_preview(plain_field, plain_field.colormap)
        assert np.array_equal(plain, base)
        assert overlays[-1]["kind"] == "markup"
        assert overlays[-1]["shape"] == "line"
        assert overlays[-1]["stroke_color"] == "#ffd54f"
        assert overlays[-1]["stroke_width"] == 3
        assert overlays[-1]["image"].startswith("data:image/png;base64,")

        shapes = json.dumps([
            {"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 3, "color": "#ff0000"},
            {"kind": "rectangle", "x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.5, "width": 2, "color": "#00ff00"},
            {"kind": "circle", "x1": 0.25, "y1": 0.55, "x2": 0.55, "y2": 0.85, "width": 2, "color": "#4fc3f7"},
            {"kind": "arrow", "x1": 0.15, "y1": 0.85, "x2": 0.85, "y2": 0.2, "width": 4, "color": "#ffffff"},
        ])
        marked_field, = node.process(input=field, shape="arrow", stroke_color="#ffffff", stroke_width=4, markup_shapes=shapes)
        marked = render_datafield_preview(marked_field, marked_field.colormap)
        assert marked.shape == base.shape
        assert not np.array_equal(marked, base)
        assert overlays[-1]["shape"] == "arrow"
        assert overlays[-1]["stroke_color"] == "#ffffff"
        assert overlays[-1]["stroke_width"] == 4

        viewport_image = ImageData(
            np.zeros((48, 48, 3), dtype=np.uint8),
            metadata={"annotation_context": {"xreal": 1e-6, "si_unit_xy": "m"}},
        )
        image_markup, = node.process(
            input=viewport_image, shape="line", stroke_color="#ff0000", stroke_width=4,
            markup_shapes=json.dumps([{"kind": "line", "x1": 0.1, "y1": 0.2, "x2": 0.9, "y2": 0.8, "width": 4, "color": "#ff0000"}]),
        )
        assert isinstance(image_markup, ImageData)
        assert image_markup.metadata["annotation_context"]["si_unit_xy"] == "m"
        assert not np.array_equal(np.asarray(image_markup), np.asarray(viewport_image))
